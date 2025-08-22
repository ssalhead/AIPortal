/**
 * 프롬프트 진화 엔진
 * 사용자 입력을 분석하여 기존 프롬프트를 자연스럽게 개선
 */

export interface PromptModification {
  additions: string[];      // 추가할 요소들
  modifications: string[];  // 변경할 요소들
  removals: string[];      // 제거할 요소들
  style?: string;          // 스타일 변경
  mood?: string;           // 분위기 변경
}

export interface EvolutionResult {
  newPrompt: string;
  negativePrompt: string;
  explanation: string;
  confidence: number;      // 0-1, 진화 결과에 대한 신뢰도
}

export class PromptEvolutionEngine {
  private commonKeywords = {
    // 동물 관련
    animals: ['강아지', '고양이', '새', '말', '토끼', '호랑이', '사자', '코끼리'],
    breeds: ['리트리버', '허스키', '불독', '시바견', '페르시안', '샴', '메인쿤'],
    
    // 행동/동작
    actions: ['뛰어노는', '걷는', '달리는', '앉아있는', '눕는', '점프하는', '헤엄치는'],
    activities: ['공놀이', '원반 따라 뛰기', '수영', '산책', '잠자기', '먹이 먹기'],
    
    // 환경/배경
    environments: ['공원', '해변', '집', '숲', '도시', '시골', '수영장', '정원'],
    weather: ['맑은', '흐린', '비오는', '눈오는', '황금빛', '일몰'],
    
    // 스타일/분위기
    styles: ['사실적인', '애니메이션', '수채화', '유화', '스케치', '만화'],
    moods: ['귀여운', '웅장한', '평화로운', '활기찬', '신비로운', '따뜻한'],
    
    // 색상/외관
    colors: ['갈색', '검은색', '흰색', '황금색', '회색', '얼룩무늬'],
    sizes: ['작은', '큰', '중간', '거대한', '미니어처'],
  };

  /**
   * 사용자 입력에서 수정 의도 추출
   */
  extractModifications(userInput: string): PromptModification {
    const input = userInput.toLowerCase();
    const modifications: PromptModification = {
      additions: [],
      modifications: [],
      removals: [],
    };

    // 1. 명시적 변경 키워드 감지
    if (input.includes('대신') || input.includes('말고')) {
      modifications.modifications.push(this.extractReplacement(userInput));
    }
    
    // 2. 추가 요청 감지
    if (input.includes('추가') || input.includes('더') || input.includes('그리고')) {
      modifications.additions.push(...this.extractAdditions(userInput));
    }
    
    // 3. 제거 요청 감지  
    if (input.includes('제거') || input.includes('빼고') || input.includes('없이')) {
      modifications.removals.push(...this.extractRemovals(userInput));
    }
    
    // 4. 종류/품종 변경 감지
    if (input.includes('종은') || input.includes('품종')) {
      const breed = this.extractBreed(userInput);
      if (breed) modifications.modifications.push(breed);
    }
    
    // 5. 행동/활동 변경 감지
    const newActivity = this.extractActivity(userInput);
    if (newActivity) modifications.additions.push(newActivity);
    
    // 6. 환경/배경 변경 감지
    const newEnvironment = this.extractEnvironment(userInput);
    if (newEnvironment) modifications.additions.push(newEnvironment);
    
    // 7. 스타일 변경 감지
    const newStyle = this.extractStyle(userInput);
    if (newStyle) modifications.style = newStyle;

    console.log('🧬 프롬프트 수정사항 추출:', {
      userInput,
      modifications,
    });

    return modifications;
  }

  /**
   * 기존 프롬프트와 수정사항을 결합하여 새로운 프롬프트 생성
   */
  evolvePrompt(basePrompt: string, userModification: string): EvolutionResult {
    console.log('✨ 프롬프트 진화 시작:', { basePrompt, userModification });
    
    const modifications = this.extractModifications(userModification);
    let newPrompt = basePrompt;
    let explanation = '';
    let confidence = 0.8; // 기본 신뢰도

    // 1. 교체/수정 적용
    if (modifications.modifications.length > 0) {
      for (const mod of modifications.modifications) {
        newPrompt = this.applyModification(newPrompt, mod);
        explanation += `${mod}로 변경. `;
        confidence += 0.1;
      }
    }

    // 2. 추가 요소 적용
    if (modifications.additions.length > 0) {
      for (const addition of modifications.additions) {
        if (!newPrompt.includes(addition)) {
          newPrompt = `${newPrompt}, ${addition}`;
          explanation += `${addition} 추가. `;
        }
      }
    }

    // 3. 제거 요소 적용
    if (modifications.removals.length > 0) {
      for (const removal of modifications.removals) {
        newPrompt = newPrompt.replace(new RegExp(removal, 'gi'), '');
        explanation += `${removal} 제거. `;
      }
    }

    // 4. 스타일 변경 적용
    if (modifications.style) {
      newPrompt = `${modifications.style} 스타일의 ${newPrompt}`;
      explanation += `${modifications.style} 스타일 적용. `;
    }

    // 5. 프롬프트 정리 (중복 제거, 문법 정리)
    newPrompt = this.cleanupPrompt(newPrompt);
    
    // 6. 네거티브 프롬프트 생성
    const negativePrompt = this.generateNegativePrompt(newPrompt);

    // 7. 신뢰도 조정
    confidence = Math.min(confidence, 1.0);
    if (modifications.additions.length === 0 && modifications.modifications.length === 0) {
      confidence = 0.5; // 큰 변화가 없으면 신뢰도 낮춤
    }

    const result: EvolutionResult = {
      newPrompt,
      negativePrompt,
      explanation: explanation || '기존 프롬프트를 기반으로 자연스럽게 발전시켰습니다.',
      confidence,
    };

    console.log('🎯 프롬프트 진화 완료:', result);
    return result;
  }

  /**
   * 주제 추출 (최초 요청에서)
   */
  extractTheme(initialPrompt: string): string {
    const prompt = initialPrompt.toLowerCase();
    
    // 1. 동물 키워드 검색
    for (const animal of this.commonKeywords.animals) {
      if (prompt.includes(animal)) {
        return animal;
      }
    }
    
    // 2. 일반적인 주제 키워드
    const themes = ['인물', '풍경', '건물', '자동차', '꽃', '나무', '음식'];
    for (const theme of themes) {
      if (prompt.includes(theme)) {
        return theme;
      }
    }
    
    // 3. 기본값
    return '이미지';
  }

  // === Private Helper Methods ===

  private extractReplacement(userInput: string): string {
    // "A 대신 B", "A 말고 B" 패턴 감지
    const patterns = [
      /(.+)\s*대신\s*(.+)/,
      /(.+)\s*말고\s*(.+)/,
      /(.+)\s*이\s*아니라\s*(.+)/,
    ];

    for (const pattern of patterns) {
      const match = userInput.match(pattern);
      if (match) {
        return match[2].trim();
      }
    }

    return '';
  }

  private extractAdditions(userInput: string): string[] {
    const additions: string[] = [];
    
    // 활동 추가
    for (const activity of this.commonKeywords.activities) {
      if (userInput.includes(activity)) {
        additions.push(activity);
      }
    }
    
    // 환경 추가
    for (const env of this.commonKeywords.environments) {
      if (userInput.includes(env)) {
        additions.push(env);
      }
    }
    
    return additions;
  }

  private extractRemovals(userInput: string): string[] {
    // 제거할 요소들 추출 (구현 필요시 확장)
    return [];
  }

  private extractBreed(userInput: string): string {
    for (const breed of this.commonKeywords.breeds) {
      if (userInput.includes(breed)) {
        return breed;
      }
    }
    return '';
  }

  private extractActivity(userInput: string): string {
    for (const activity of this.commonKeywords.activities) {
      if (userInput.includes(activity)) {
        return activity;
      }
    }
    
    // 동작 키워드 감지
    for (const action of this.commonKeywords.actions) {
      if (userInput.includes(action)) {
        return action;
      }
    }
    
    return '';
  }

  private extractEnvironment(userInput: string): string {
    for (const env of this.commonKeywords.environments) {
      if (userInput.includes(env)) {
        return env;
      }
    }
    return '';
  }

  private extractStyle(userInput: string): string {
    for (const style of this.commonKeywords.styles) {
      if (userInput.includes(style)) {
        return style;
      }
    }
    return '';
  }

  private applyModification(prompt: string, modification: string): string {
    // 품종 변경의 경우
    if (this.commonKeywords.breeds.includes(modification)) {
      // 기존 품종을 새 품종으로 교체
      for (const breed of this.commonKeywords.breeds) {
        if (prompt.includes(breed) && breed !== modification) {
          return prompt.replace(breed, modification);
        }
      }
      // 품종이 명시되지 않았다면 동물 뒤에 추가
      for (const animal of this.commonKeywords.animals) {
        if (prompt.includes(animal)) {
          return prompt.replace(animal, `${modification} ${animal}`);
        }
      }
    }
    
    return prompt;
  }

  private cleanupPrompt(prompt: string): string {
    return prompt
      .replace(/,\s*,/g, ',') // 중복 쉼표 제거
      .replace(/\s+/g, ' ')   // 연속 공백 제거
      .trim();
  }

  private generateNegativePrompt(prompt: string): string {
    // 기본 네거티브 프롬프트
    const baseNegative = 'blurry, low quality, distorted, deformed';
    
    // 프롬프트에 따른 맞춤 네거티브 프롬프트 (추후 확장)
    if (prompt.includes('강아지') || prompt.includes('고양이')) {
      return `${baseNegative}, multiple heads, extra limbs`;
    }
    
    return baseNegative;
  }
}

// 싱글톤 인스턴스 생성
export const promptEvolutionEngine = new PromptEvolutionEngine();