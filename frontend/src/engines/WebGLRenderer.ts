/**
 * Canvas v4.0 다중 이미지 편집 WebGL 렌더링 엔진
 * 고성능 레이어 합성 및 실시간 편집을 위한 WebGL 기반 렌더러
 */

import type { 
  Layer, 
  LayerContainer, 
  RenderSettings, 
  LayerCache,
  LayerTransform,
  BoundingBox 
} from '../types/layer';

// ============= WebGL 컨텍스트 및 설정 =============

interface WebGLResources {
  gl: WebGLRenderingContext | WebGL2RenderingContext;
  canvas: HTMLCanvasElement;
  
  // 프로그램 및 셰이더
  programs: Map<string, WebGLProgram>;
  shaders: Map<string, WebGLShader>;
  
  // 버퍼 및 텍스처
  vertexBuffer: WebGLBuffer;
  textures: Map<string, WebGLTexture>;
  framebuffers: Map<string, WebGLFramebuffer>;
  
  // 유니폼 및 어트리뷰트 위치
  uniformLocations: Map<string, WebGLUniformLocation>;
  attributeLocations: Map<string, number>;
}

interface RenderBatch {
  layerIds: string[];
  program: WebGLProgram;
  uniforms: Record<string, any>;
  textures: WebGLTexture[];
}

// ============= 셰이더 소스 코드 =============

const VERTEX_SHADER_SOURCE = `
precision mediump float;

attribute vec2 a_position;
attribute vec2 a_texCoord;

uniform mat3 u_transform;
uniform vec2 u_resolution;

varying vec2 v_texCoord;

void main() {
  // 좌표 변환 적용
  vec3 position = u_transform * vec3(a_position, 1.0);
  
  // 스크린 좌표로 변환
  vec2 clipspace = ((position.xy / u_resolution) * 2.0) - 1.0;
  gl_Position = vec4(clipspace * vec2(1, -1), 0, 1);
  
  v_texCoord = a_texCoord;
}
`;

const FRAGMENT_SHADER_BASIC = `
precision mediump float;

uniform sampler2D u_texture;
uniform float u_opacity;
uniform vec4 u_colorMultiplier;

varying vec2 v_texCoord;

void main() {
  vec4 color = texture2D(u_texture, v_texCoord);
  color *= u_colorMultiplier;
  color.a *= u_opacity;
  gl_FragColor = color;
}
`;

const FRAGMENT_SHADER_BLEND = `
precision mediump float;

uniform sampler2D u_texture;
uniform sampler2D u_background;
uniform float u_opacity;
uniform int u_blendMode;

varying vec2 v_texCoord;

vec3 blendMultiply(vec3 base, vec3 blend) {
  return base * blend;
}

vec3 blendScreen(vec3 base, vec3 blend) {
  return 1.0 - (1.0 - base) * (1.0 - blend);
}

vec3 blendOverlay(vec3 base, vec3 blend) {
  return mix(
    2.0 * base * blend,
    1.0 - 2.0 * (1.0 - base) * (1.0 - blend),
    step(0.5, base)
  );
}

vec3 applyBlendMode(vec3 base, vec3 blend, int mode) {
  if (mode == 1) return blendMultiply(base, blend);
  if (mode == 2) return blendScreen(base, blend);
  if (mode == 3) return blendOverlay(base, blend);
  return blend; // Normal blend
}

void main() {
  vec4 sourceColor = texture2D(u_texture, v_texCoord);
  vec4 backgroundColor = texture2D(u_background, v_texCoord);
  
  vec3 blended = applyBlendMode(
    backgroundColor.rgb, 
    sourceColor.rgb, 
    u_blendMode
  );
  
  float alpha = sourceColor.a * u_opacity;
  vec3 final = mix(backgroundColor.rgb, blended, alpha);
  
  gl_FragColor = vec4(final, backgroundColor.a + alpha * (1.0 - backgroundColor.a));
}
`;

// ============= 필터 셰이더들 =============

const FRAGMENT_SHADER_BLUR = `
precision mediump float;

uniform sampler2D u_texture;
uniform vec2 u_resolution;
uniform float u_blurAmount;

varying vec2 v_texCoord;

void main() {
  vec2 onePixel = vec2(1.0) / u_resolution;
  vec4 color = vec4(0.0);
  
  // 가우시안 블러 근사
  color += texture2D(u_texture, v_texCoord + onePixel * vec2(-1, -1)) * 0.077;
  color += texture2D(u_texture, v_texCoord + onePixel * vec2(0, -1)) * 0.123;
  color += texture2D(u_texture, v_texCoord + onePixel * vec2(1, -1)) * 0.077;
  
  color += texture2D(u_texture, v_texCoord + onePixel * vec2(-1, 0)) * 0.123;
  color += texture2D(u_texture, v_texCoord) * 0.20;
  color += texture2D(u_texture, v_texCoord + onePixel * vec2(1, 0)) * 0.123;
  
  color += texture2D(u_texture, v_texCoord + onePixel * vec2(-1, 1)) * 0.077;
  color += texture2D(u_texture, v_texCoord + onePixel * vec2(0, 1)) * 0.123;
  color += texture2D(u_texture, v_texCoord + onePixel * vec2(1, 1)) * 0.077;
  
  gl_FragColor = mix(texture2D(u_texture, v_texCoord), color, u_blurAmount);
}
`;

const FRAGMENT_SHADER_COLOR_ADJUST = `
precision mediump float;

uniform sampler2D u_texture;
uniform float u_brightness;
uniform float u_contrast;
uniform float u_saturation;
uniform float u_hue;

varying vec2 v_texCoord;

vec3 rgb2hsv(vec3 c) {
  vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
  vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
  vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
  
  float d = q.x - min(q.w, q.y);
  float e = 1.0e-10;
  return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 hsv2rgb(vec3 c) {
  vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
  vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
  return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
  vec4 color = texture2D(u_texture, v_texCoord);
  
  // 밝기 조정
  color.rgb += u_brightness;
  
  // 대비 조정
  color.rgb = (color.rgb - 0.5) * u_contrast + 0.5;
  
  // HSV 변환
  vec3 hsv = rgb2hsv(color.rgb);
  
  // 채도 및 색조 조정
  hsv.y *= u_saturation;
  hsv.x += u_hue;
  hsv.x = fract(hsv.x);
  
  // RGB로 다시 변환
  color.rgb = hsv2rgb(hsv);
  
  gl_FragColor = color;
}
`;

// ============= WebGL 렌더러 클래스 =============

export class WebGLRenderer {
  private resources: WebGLResources | null = null;
  private settings: RenderSettings;
  private renderBatches: RenderBatch[] = [];
  private textureCache: Map<string, WebGLTexture> = new Map();
  private isInitialized = false;
  
  // 성능 메트릭
  private performanceStats = {
    frameTime: 0,
    drawCalls: 0,
    textureSwaps: 0,
    lastFrameStart: 0
  };

  constructor(canvas: HTMLCanvasElement, settings: RenderSettings) {
    this.settings = settings;
    this.initialize(canvas);
  }

  // ============= 초기화 =============

  private initialize(canvas: HTMLCanvasElement): boolean {
    try {
      const gl = this.getWebGLContext(canvas);
      if (!gl) {
        console.warn('WebGL을 사용할 수 없습니다. Canvas 2D로 폴백합니다.');
        return false;
      }

      this.resources = {
        gl,
        canvas,
        programs: new Map(),
        shaders: new Map(),
        vertexBuffer: this.createVertexBuffer(gl),
        textures: new Map(),
        framebuffers: new Map(),
        uniformLocations: new Map(),
        attributeLocations: new Map()
      };

      // 기본 프로그램 생성
      this.createShaderPrograms();
      
      // WebGL 설정
      this.setupWebGLState(gl);
      
      this.isInitialized = true;
      return true;
      
    } catch (error) {
      console.error('WebGL 렌더러 초기화 실패:', error);
      return false;
    }
  }

  private getWebGLContext(canvas: HTMLCanvasElement): WebGLRenderingContext | WebGL2RenderingContext | null {
    const contextOptions = {
      alpha: true,
      premultipliedAlpha: false,
      preserveDrawingBuffer: false,
      antialias: this.settings.enableAntiAlias,
      powerPreference: 'high-performance' as WebGLPowerPreference
    };

    // WebGL2를 우선 시도
    let gl = canvas.getContext('webgl2', contextOptions) as WebGL2RenderingContext;
    
    if (!gl) {
      // WebGL1 폴백
      gl = canvas.getContext('webgl', contextOptions) as WebGLRenderingContext;
    }

    return gl;
  }

  private createVertexBuffer(gl: WebGLRenderingContext): WebGLBuffer {
    const vertices = new Float32Array([
      // 위치(x, y), 텍스처 좌표(u, v)
      -1, -1,  0, 1,  // 좌하단
       1, -1,  1, 1,  // 우하단
      -1,  1,  0, 0,  // 좌상단
       1,  1,  1, 0   // 우상단
    ]);

    const buffer = gl.createBuffer();
    if (!buffer) {
      throw new Error('정점 버퍼 생성 실패');
    }

    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW);
    
    return buffer;
  }

  private createShaderPrograms(): void {
    if (!this.resources) return;

    const programs = [
      { name: 'basic', vs: VERTEX_SHADER_SOURCE, fs: FRAGMENT_SHADER_BASIC },
      { name: 'blend', vs: VERTEX_SHADER_SOURCE, fs: FRAGMENT_SHADER_BLEND },
      { name: 'blur', vs: VERTEX_SHADER_SOURCE, fs: FRAGMENT_SHADER_BLUR },
      { name: 'colorAdjust', vs: VERTEX_SHADER_SOURCE, fs: FRAGMENT_SHADER_COLOR_ADJUST }
    ];

    programs.forEach(({ name, vs, fs }) => {
      const program = this.createShaderProgram(vs, fs);
      if (program) {
        this.resources!.programs.set(name, program);
        this.setupProgramLocations(name, program);
      }
    });
  }

  private createShaderProgram(vertexSource: string, fragmentSource: string): WebGLProgram | null {
    if (!this.resources) return null;
    
    const { gl } = this.resources;
    
    const vertexShader = this.createShader(gl, gl.VERTEX_SHADER, vertexSource);
    const fragmentShader = this.createShader(gl, gl.FRAGMENT_SHADER, fragmentSource);
    
    if (!vertexShader || !fragmentShader) {
      return null;
    }

    const program = gl.createProgram();
    if (!program) return null;

    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);

    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error('셰이더 프로그램 링크 실패:', gl.getProgramInfoLog(program));
      gl.deleteProgram(program);
      return null;
    }

    return program;
  }

  private createShader(gl: WebGLRenderingContext, type: number, source: string): WebGLShader | null {
    const shader = gl.createShader(type);
    if (!shader) return null;

    gl.shaderSource(shader, source);
    gl.compileShader(shader);

    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      console.error('셰이더 컴파일 실패:', gl.getShaderInfoLog(shader));
      gl.deleteShader(shader);
      return null;
    }

    return shader;
  }

  private setupProgramLocations(name: string, program: WebGLProgram): void {
    if (!this.resources) return;
    
    const { gl } = this.resources;
    
    // 어트리뷰트 위치
    const positionLoc = gl.getAttribLocation(program, 'a_position');
    const texCoordLoc = gl.getAttribLocation(program, 'a_texCoord');
    
    this.resources.attributeLocations.set(`${name}_position`, positionLoc);
    this.resources.attributeLocations.set(`${name}_texCoord`, texCoordLoc);
    
    // 유니폼 위치들
    const uniformNames = [
      'u_transform', 'u_resolution', 'u_texture', 'u_opacity',
      'u_colorMultiplier', 'u_background', 'u_blendMode',
      'u_blurAmount', 'u_brightness', 'u_contrast', 'u_saturation', 'u_hue'
    ];
    
    uniformNames.forEach(uniformName => {
      const location = gl.getUniformLocation(program, uniformName);
      if (location) {
        this.resources!.uniformLocations.set(`${name}_${uniformName}`, location);
      }
    });
  }

  private setupWebGLState(gl: WebGLRenderingContext): void {
    // 블렌딩 활성화
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    
    // 깊이 테스트 비활성화 (2D 렌더링)
    gl.disable(gl.DEPTH_TEST);
    
    // 컬링 비활성화
    gl.disable(gl.CULL_FACE);
    
    // 뷰포트 설정
    gl.viewport(0, 0, gl.canvas.width, gl.canvas.height);
    
    // 배경색 설정
    gl.clearColor(0, 0, 0, 0);
  }

  // ============= 렌더링 메인 함수 =============

  public render(container: LayerContainer): void {
    if (!this.isInitialized || !this.resources) {
      console.warn('WebGL 렌더러가 초기화되지 않았습니다.');
      return;
    }

    this.performanceStats.lastFrameStart = performance.now();
    this.performanceStats.drawCalls = 0;
    this.performanceStats.textureSwaps = 0;

    const { gl } = this.resources;
    
    // 캔버스 클리어
    gl.clear(gl.COLOR_BUFFER_BIT);
    
    // 배경색 렌더링
    this.renderBackground(container);
    
    // 레이어들을 Z 순서대로 렌더링
    const sortedLayers = this.getSortedLayers(container);
    
    // 렌더링 배치 최적화
    this.buildRenderBatches(sortedLayers);
    
    // 배치별 렌더링 실행
    this.executeRenderBatches();
    
    // 성능 메트릭 업데이트
    this.updatePerformanceStats();
  }

  private renderBackground(container: LayerContainer): void {
    if (!this.resources) return;
    
    const { gl } = this.resources;
    const backgroundColor = container.canvas.backgroundColor;
    
    // 배경색 파싱
    const color = this.parseColor(backgroundColor);
    gl.clearColor(color.r, color.g, color.b, color.a);
    gl.clear(gl.COLOR_BUFFER_BIT);
  }

  private getSortedLayers(container: LayerContainer): Layer[] {
    return container.layerOrder
      .map(id => container.layers[id])
      .filter(layer => layer && layer.state.visible)
      .sort((a, b) => a.zIndex - b.zIndex);
  }

  private buildRenderBatches(layers: Layer[]): void {
    this.renderBatches = [];
    
    // 간단한 배칭: 동일한 블렌드 모드별로 그룹화
    const batches = new Map<string, Layer[]>();
    
    layers.forEach(layer => {
      const batchKey = `${layer.state.blendMode}_${this.needsSpecialShader(layer)}`;
      if (!batches.has(batchKey)) {
        batches.set(batchKey, []);
      }
      batches.get(batchKey)!.push(layer);
    });
    
    // 배치 생성
    batches.forEach((batchLayers, key) => {
      const [blendMode, needsSpecial] = key.split('_');
      const programName = needsSpecial === 'true' ? this.getSpecialProgramName(batchLayers[0]) : 'basic';
      const program = this.resources!.programs.get(programName);
      
      if (program) {
        this.renderBatches.push({
          layerIds: batchLayers.map(l => l.id),
          program,
          uniforms: this.buildBatchUniforms(batchLayers, blendMode),
          textures: []
        });
      }
    });
  }

  private executeRenderBatches(): void {
    this.renderBatches.forEach(batch => {
      this.renderBatch(batch);
    });
  }

  private renderBatch(batch: RenderBatch): void {
    if (!this.resources) return;
    
    const { gl } = this.resources;
    
    // 프로그램 사용
    gl.useProgram(batch.program);
    this.performanceStats.drawCalls++;
    
    // 버퍼 바인딩
    gl.bindBuffer(gl.ARRAY_BUFFER, this.resources.vertexBuffer);
    
    // 어트리뷰트 설정 (각 배치별로 동일)
    this.setupVertexAttributes(batch.program);
    
    // 각 레이어별로 렌더링
    batch.layerIds.forEach(layerId => {
      this.renderLayer(layerId, batch.program, batch.uniforms);
    });
  }

  private renderLayer(layerId: string, program: WebGLProgram, batchUniforms: Record<string, any>): void {
    if (!this.resources) return;
    
    const { gl } = this.resources;
    
    // 레이어별 텍스처 바인딩
    const texture = this.getLayerTexture(layerId);
    if (!texture) return;
    
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, texture);
    this.performanceStats.textureSwaps++;
    
    // 유니폼 설정
    this.setLayerUniforms(program, layerId, batchUniforms);
    
    // 렌더링 실행
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
  }

  private setupVertexAttributes(program: WebGLProgram): void {
    if (!this.resources) return;
    
    const { gl } = this.resources;
    const programName = this.getProgramName(program);
    
    const positionLoc = this.resources.attributeLocations.get(`${programName}_position`);
    const texCoordLoc = this.resources.attributeLocations.get(`${programName}_texCoord`);
    
    if (positionLoc !== undefined && positionLoc >= 0) {
      gl.enableVertexAttribArray(positionLoc);
      gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, 16, 0);
    }
    
    if (texCoordLoc !== undefined && texCoordLoc >= 0) {
      gl.enableVertexAttribArray(texCoordLoc);
      gl.vertexAttribPointer(texCoordLoc, 2, gl.FLOAT, false, 16, 8);
    }
  }

  // ============= 텍스처 관리 =============

  private getLayerTexture(layerId: string): WebGLTexture | null {
    return this.textureCache.get(layerId) || null;
  }

  public createTextureFromImage(layerId: string, image: HTMLImageElement | HTMLCanvasElement): WebGLTexture | null {
    if (!this.resources) return null;
    
    const { gl } = this.resources;
    
    const texture = gl.createTexture();
    if (!texture) return null;
    
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
    
    // 텍스처 파라미터 설정
    if (this.isPowerOf2(image.width) && this.isPowerOf2(image.height)) {
      gl.generateMipmap(gl.TEXTURE_2D);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    } else {
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    }
    
    if (this.settings.enableBilinearFiltering) {
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    } else {
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    }
    
    // 캐시에 저장
    this.textureCache.set(layerId, texture);
    
    return texture;
  }

  public deleteTexture(layerId: string): void {
    const texture = this.textureCache.get(layerId);
    if (texture && this.resources) {
      this.resources.gl.deleteTexture(texture);
      this.textureCache.delete(layerId);
    }
  }

  // ============= 유틸리티 메서드 =============

  private needsSpecialShader(layer: Layer): boolean {
    // 필터나 특별한 효과가 필요한 경우 체크
    return !!(layer.style?.filters || layer.mask || layer.state.blendMode !== 'normal');
  }

  private getSpecialProgramName(layer: Layer): string {
    if (layer.style?.filters) {
      if (layer.style.filters.blur && layer.style.filters.blur > 0) {
        return 'blur';
      }
      return 'colorAdjust';
    }
    if (layer.state.blendMode !== 'normal') {
      return 'blend';
    }
    return 'basic';
  }

  private getProgramName(program: WebGLProgram): string {
    for (const [name, prog] of this.resources!.programs) {
      if (prog === program) return name;
    }
    return 'basic';
  }

  private buildBatchUniforms(layers: Layer[], blendMode: string): Record<string, any> {
    return {
      blendMode,
      resolution: [this.resources!.canvas.width, this.resources!.canvas.height]
    };
  }

  private setLayerUniforms(program: WebGLProgram, layerId: string, batchUniforms: Record<string, any>): void {
    // 실제 레이어 데이터를 기반으로 유니폼 설정
    // 여기서는 기본 구조만 제공
  }

  private parseColor(colorString: string): { r: number; g: number; b: number; a: number } {
    // 색상 문자열 파싱 (예: "#ffffff", "rgba(255,255,255,1)")
    if (colorString.startsWith('#')) {
      const hex = colorString.slice(1);
      const r = parseInt(hex.slice(0, 2), 16) / 255;
      const g = parseInt(hex.slice(2, 4), 16) / 255;
      const b = parseInt(hex.slice(4, 6), 16) / 255;
      return { r, g, b, a: 1.0 };
    }
    
    // 기본값 반환
    return { r: 1, g: 1, b: 1, a: 1 };
  }

  private isPowerOf2(value: number): boolean {
    return (value & (value - 1)) === 0;
  }

  private updatePerformanceStats(): void {
    this.performanceStats.frameTime = performance.now() - this.performanceStats.lastFrameStart;
  }

  // ============= 공개 API =============

  public getPerformanceStats() {
    return { ...this.performanceStats };
  }

  public updateSettings(newSettings: Partial<RenderSettings>): void {
    this.settings = { ...this.settings, ...newSettings };
    
    // 설정 변경에 따른 WebGL 상태 업데이트
    if (this.resources) {
      this.setupWebGLState(this.resources.gl);
    }
  }

  public cleanup(): void {
    if (!this.resources) return;
    
    const { gl } = this.resources;
    
    // 텍스처 정리
    this.textureCache.forEach(texture => gl.deleteTexture(texture));
    this.textureCache.clear();
    
    // 프로그램 정리
    this.resources.programs.forEach(program => gl.deleteProgram(program));
    this.resources.programs.clear();
    
    // 버퍼 정리
    gl.deleteBuffer(this.resources.vertexBuffer);
    
    this.resources = null;
    this.isInitialized = false;
  }
}

export default WebGLRenderer;