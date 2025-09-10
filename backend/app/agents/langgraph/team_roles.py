"""
LangGraph 개발팀 역할 정의 및 관리 시스템

점진적 마이그레이션 과정에서 효율적인 개발팀 분할과 역할 관리를 위한 시스템입니다.
각 팀원의 전문성과 역할에 따라 LangGraph와 Legacy 시스템을 동시에 개발할 수 있도록 지원합니다.
"""

from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DeveloperRole(Enum):
    """개발자 역할 분류"""
    LANGGRAPH_ARCHITECT = "langgraph_architect"      # LangGraph 아키텍처 전문가
    LANGGRAPH_DEVELOPER = "langgraph_developer"      # LangGraph 개발자
    LEGACY_MAINTAINER = "legacy_maintainer"         # Legacy 시스템 유지보수
    HYBRID_DEVELOPER = "hybrid_developer"           # 하이브리드 개발 (양쪽 모두)
    FEATURE_FLAG_MANAGER = "feature_flag_manager"   # Feature Flag 관리자
    PERFORMANCE_ANALYST = "performance_analyst"     # 성능 분석가
    TESTING_SPECIALIST = "testing_specialist"       # 테스트 전문가
    QA_ENGINEER = "qa_engineer"                     # QA 엔지니어


class TeamPhase(Enum):
    """개발 단계별 팀 구성"""
    PHASE_0_FOUNDATION = "phase_0_foundation"       # Phase 0: 기반 구축
    PHASE_1_WEB_SEARCH = "phase_1_web_search"      # Phase 1: WebSearch Hybrid
    PHASE_2_CANVAS = "phase_2_canvas"              # Phase 2: Canvas System
    PHASE_3_INFORMATION_GAP = "phase_3_info_gap"   # Phase 3: Information Gap
    PHASE_4_SUPERVISOR = "phase_4_supervisor"      # Phase 4: Supervisor Complete


@dataclass
class DeveloperProfile:
    """개발자 프로필"""
    user_id: str
    name: str
    email: str
    primary_role: DeveloperRole
    secondary_roles: List[DeveloperRole]
    langgraph_experience: int  # 0-10 점
    legacy_experience: int     # 0-10 점
    specialties: List[str]
    current_assignments: List[str]
    availability_hours_per_week: int
    timezone: str
    preferred_work_hours: str  # "09:00-18:00 KST"


@dataclass
class TeamAssignment:
    """팀 배정 정보"""
    phase: TeamPhase
    team_name: str
    team_lead: str
    members: List[str]
    responsibilities: List[str]
    deliverables: List[str]
    start_date: datetime
    target_completion_date: datetime
    current_status: str
    progress_percentage: int


class LangGraphTeamManager:
    """LangGraph 개발팀 관리 시스템"""
    
    def __init__(self):
        self.developers: Dict[str, DeveloperProfile] = {}
        self.team_assignments: Dict[str, TeamAssignment] = {}
        self.phase_requirements: Dict[TeamPhase, Dict[str, any]] = {}
        
        # 초기 팀 구성 및 요구사항 설정
        self._initialize_phase_requirements()
        self._setup_demo_team()  # 데모용 팀 설정

    def _initialize_phase_requirements(self):
        """각 단계별 팀 요구사항 정의"""
        
        self.phase_requirements = {
            TeamPhase.PHASE_0_FOUNDATION: {
                "required_roles": [
                    DeveloperRole.LANGGRAPH_ARCHITECT,
                    DeveloperRole.FEATURE_FLAG_MANAGER,
                    DeveloperRole.PERFORMANCE_ANALYST
                ],
                "team_size": 3,
                "duration_weeks": 1,
                "key_deliverables": [
                    "Feature Flag 시스템 구축",
                    "LangGraph 모니터링 시스템",
                    "PostgreSQL 체크포인터 설정",
                    "기본 인프라 구축"
                ],
                "success_criteria": [
                    "Feature Flag 정상 동작",
                    "모니터링 대시보드 구축",
                    "체크포인터 테이블 생성",
                    "기본 LangGraph 에이전트 테스트"
                ]
            },
            
            TeamPhase.PHASE_1_WEB_SEARCH: {
                "required_roles": [
                    DeveloperRole.LANGGRAPH_DEVELOPER,
                    DeveloperRole.LEGACY_MAINTAINER,
                    DeveloperRole.TESTING_SPECIALIST
                ],
                "team_size": 4,
                "duration_weeks": 3,
                "key_deliverables": [
                    "LangGraph WebSearchAgent 구현",
                    "하이브리드 라우팅 시스템",
                    "자동 fallback 메커니즘",
                    "성능 비교 시스템"
                ],
                "success_criteria": [
                    "10% 트래픽에서 안정적 동작",
                    "Legacy 대비 성능 동등 이상",
                    "자동 fallback 100% 성공률",
                    "A/B 테스트 결과 양호"
                ]
            },
            
            TeamPhase.PHASE_2_CANVAS: {
                "required_roles": [
                    DeveloperRole.LANGGRAPH_DEVELOPER,
                    DeveloperRole.HYBRID_DEVELOPER,
                    DeveloperRole.QA_ENGINEER
                ],
                "team_size": 5,
                "duration_weeks": 2.5,
                "key_deliverables": [
                    "Canvas LangGraph 워크플로우",
                    "Information Gap LangGraph 분석",
                    "병렬 처리 워크플로우",
                    "통합 테스트 스위트"
                ],
                "success_criteria": [
                    "Canvas 기능 완전 이관",
                    "정보 분석 정확도 향상",
                    "병렬 처리 성능 30% 향상",
                    "사용자 만족도 90% 이상"
                ]
            },
            
            TeamPhase.PHASE_3_INFORMATION_GAP: {
                "required_roles": [
                    DeveloperRole.LANGGRAPH_DEVELOPER,
                    DeveloperRole.PERFORMANCE_ANALYST,
                    DeveloperRole.TESTING_SPECIALIST
                ],
                "team_size": 3,
                "duration_weeks": 3,
                "key_deliverables": [
                    "Tool-calling 기반 핸드오프",
                    "고급 상태 관리",
                    "멀티모달 RAG 통합",
                    "성능 최적화"
                ],
                "success_criteria": [
                    "Tool-calling 정확도 95%+",
                    "상태 영속성 100%",
                    "RAG 응답 품질 개선",
                    "전체 시스템 안정성 확보"
                ]
            },
            
            TeamPhase.PHASE_4_SUPERVISOR: {
                "required_roles": [
                    DeveloperRole.LANGGRAPH_ARCHITECT,
                    DeveloperRole.HYBRID_DEVELOPER,
                    DeveloperRole.QA_ENGINEER,
                    DeveloperRole.PERFORMANCE_ANALYST
                ],
                "team_size": 6,
                "duration_weeks": 1.5,
                "key_deliverables": [
                    "SupervisorAgent 완전 LangGraph 전환",
                    "Legacy 시스템 단계적 제거",
                    "전체 시스템 통합 테스트",
                    "프로덕션 배포 준비"
                ],
                "success_criteria": [
                    "100% LangGraph 동작",
                    "Legacy 의존성 제거",
                    "성능 기준 달성",
                    "프로덕션 배포 성공"
                ]
            }
        }

    def _setup_demo_team(self):
        """데모용 개발팀 설정"""
        
        # 샘플 개발자들 추가
        demo_developers = [
            DeveloperProfile(
                user_id="dev_langgraph_architect_01",
                name="김아키텍트",
                email="architect@aiportal.com",
                primary_role=DeveloperRole.LANGGRAPH_ARCHITECT,
                secondary_roles=[DeveloperRole.PERFORMANCE_ANALYST],
                langgraph_experience=9,
                legacy_experience=7,
                specialties=["LangGraph StateGraph", "워크플로우 설계", "시스템 아키텍처"],
                current_assignments=["Phase 0 기반 구축"],
                availability_hours_per_week=40,
                timezone="KST",
                preferred_work_hours="09:00-18:00 KST"
            ),
            
            DeveloperProfile(
                user_id="dev_langgraph_dev_01",
                name="이개발자",
                email="dev1@aiportal.com",
                primary_role=DeveloperRole.LANGGRAPH_DEVELOPER,
                secondary_roles=[DeveloperRole.TESTING_SPECIALIST],
                langgraph_experience=8,
                legacy_experience=6,
                specialties=["StateGraph 구현", "에이전트 개발", "테스트 자동화"],
                current_assignments=["Phase 1 WebSearch Agent"],
                availability_hours_per_week=40,
                timezone="KST",
                preferred_work_hours="10:00-19:00 KST"
            ),
            
            DeveloperProfile(
                user_id="dev_legacy_maintainer_01",
                name="박레거시",
                email="legacy@aiportal.com",
                primary_role=DeveloperRole.LEGACY_MAINTAINER,
                secondary_roles=[DeveloperRole.HYBRID_DEVELOPER],
                langgraph_experience=5,
                legacy_experience=9,
                specialties=["기존 시스템 분석", "마이그레이션 전략", "호환성 관리"],
                current_assignments=["Legacy 시스템 유지"],
                availability_hours_per_week=40,
                timezone="KST",
                preferred_work_hours="09:00-18:00 KST"
            ),
            
            DeveloperProfile(
                user_id="dev_feature_flag_manager_01",
                name="최피처플래그",
                email="featureflag@aiportal.com",
                primary_role=DeveloperRole.FEATURE_FLAG_MANAGER,
                secondary_roles=[DeveloperRole.PERFORMANCE_ANALYST],
                langgraph_experience=6,
                legacy_experience=7,
                specialties=["Feature Flag 시스템", "A/B 테스트", "점진적 배포"],
                current_assignments=["Feature Flag 관리"],
                availability_hours_per_week=35,
                timezone="KST",
                preferred_work_hours="10:00-19:00 KST"
            ),
            
            DeveloperProfile(
                user_id="dev_qa_engineer_01",
                name="정QA엔지니어",
                email="qa@aiportal.com",
                primary_role=DeveloperRole.QA_ENGINEER,
                secondary_roles=[DeveloperRole.TESTING_SPECIALIST],
                langgraph_experience=7,
                legacy_experience=8,
                specialties=["통합 테스트", "성능 테스트", "사용자 테스트"],
                current_assignments=["품질 보증"],
                availability_hours_per_week=40,
                timezone="KST",
                preferred_work_hours="09:30-18:30 KST"
            )
        ]
        
        # 개발자들을 시스템에 등록
        for dev in demo_developers:
            self.register_developer(dev)
        
        # 초기 팀 배정
        self._assign_phase_teams()

    def register_developer(self, developer: DeveloperProfile):
        """개발자 등록"""
        self.developers[developer.user_id] = developer
        logger.info(f"개발자 등록: {developer.name} ({developer.primary_role.value})")

    def _assign_phase_teams(self):
        """각 단계별 팀 배정"""
        
        # Phase 0 팀 구성
        phase_0_team = TeamAssignment(
            phase=TeamPhase.PHASE_0_FOUNDATION,
            team_name="Foundation Team",
            team_lead="dev_langgraph_architect_01",
            members=[
                "dev_langgraph_architect_01",
                "dev_feature_flag_manager_01",
                "dev_qa_engineer_01"
            ],
            responsibilities=[
                "Feature Flag 시스템 구축 및 관리",
                "LangGraph 모니터링 시스템 개발",
                "PostgreSQL 체크포인터 설정",
                "기본 인프라 및 도구 구축"
            ],
            deliverables=[
                "완전한 Feature Flag 시스템",
                "실시간 성능 모니터링 대시보드",
                "LangGraph 체크포인터 테이블",
                "개발 환경 설정 가이드"
            ],
            start_date=datetime(2025, 9, 10),
            target_completion_date=datetime(2025, 9, 17),
            current_status="완료",
            progress_percentage=100
        )
        
        # Phase 1 팀 구성
        phase_1_team = TeamAssignment(
            phase=TeamPhase.PHASE_1_WEB_SEARCH,
            team_name="WebSearch Hybrid Team",
            team_lead="dev_langgraph_dev_01",
            members=[
                "dev_langgraph_dev_01",
                "dev_legacy_maintainer_01",
                "dev_feature_flag_manager_01",
                "dev_qa_engineer_01"
            ],
            responsibilities=[
                "LangGraph WebSearchAgent 구현",
                "하이브리드 라우팅 시스템 개발",
                "자동 fallback 메커니즘 구축",
                "성능 비교 및 A/B 테스트"
            ],
            deliverables=[
                "완전한 LangGraph WebSearchAgent",
                "Feature Flag 기반 하이브리드 시스템",
                "자동 fallback 및 에러 처리",
                "성능 비교 리포트"
            ],
            start_date=datetime(2025, 9, 17),
            target_completion_date=datetime(2025, 10, 8),
            current_status="완료",
            progress_percentage=100
        )
        
        # Phase 2 팀 구성 (다음 단계)
        phase_2_team = TeamAssignment(
            phase=TeamPhase.PHASE_2_CANVAS,
            team_name="Canvas & Information Analysis Team",
            team_lead="dev_langgraph_architect_01",
            members=[
                "dev_langgraph_architect_01",
                "dev_langgraph_dev_01",
                "dev_legacy_maintainer_01",
                "dev_feature_flag_manager_01",
                "dev_qa_engineer_01"
            ],
            responsibilities=[
                "Canvas LangGraph 워크플로우 개발",
                "Information Gap Analyzer LangGraph 전환",
                "병렬 처리 워크플로우 구현",
                "통합 테스트 및 품질 보증"
            ],
            deliverables=[
                "Canvas LangGraph 에이전트",
                "정보 분석 LangGraph 시스템",
                "병렬 처리 최적화",
                "통합 테스트 스위트"
            ],
            start_date=datetime(2025, 10, 8),
            target_completion_date=datetime(2025, 10, 25),
            current_status="대기중",
            progress_percentage=0
        )
        
        # 팀 배정 등록
        self.team_assignments["phase_0"] = phase_0_team
        self.team_assignments["phase_1"] = phase_1_team
        self.team_assignments["phase_2"] = phase_2_team

    def get_team_for_phase(self, phase: TeamPhase) -> Optional[TeamAssignment]:
        """특정 단계의 팀 정보 조회"""
        phase_key = f"phase_{phase.value.split('_')[1]}"
        return self.team_assignments.get(phase_key)

    def get_developer_profile(self, user_id: str) -> Optional[DeveloperProfile]:
        """개발자 프로필 조회"""
        return self.developers.get(user_id)

    def get_developers_by_role(self, role: DeveloperRole) -> List[DeveloperProfile]:
        """역할별 개발자 목록 조회"""
        return [
            dev for dev in self.developers.values() 
            if dev.primary_role == role or role in dev.secondary_roles
        ]

    def get_current_team_status(self) -> Dict[str, any]:
        """현재 팀 상태 전체 조회"""
        return {
            "total_developers": len(self.developers),
            "active_phases": len([t for t in self.team_assignments.values() if t.current_status in ["진행중", "완료"]]),
            "phase_progress": {
                phase_id: {
                    "team_name": team.team_name,
                    "status": team.current_status,
                    "progress": team.progress_percentage,
                    "team_size": len(team.members),
                    "deliverables_count": len(team.deliverables)
                }
                for phase_id, team in self.team_assignments.items()
            },
            "role_distribution": {
                role.value: len(self.get_developers_by_role(role))
                for role in DeveloperRole
            }
        }

    def assign_developer_to_phase(self, user_id: str, phase: TeamPhase):
        """개발자를 특정 단계에 배정"""
        phase_key = f"phase_{phase.value.split('_')[1]}"
        if phase_key in self.team_assignments:
            team = self.team_assignments[phase_key]
            if user_id not in team.members:
                team.members.append(user_id)
                
                # 개발자 현재 배정 업데이트
                if user_id in self.developers:
                    dev = self.developers[user_id]
                    if team.team_name not in dev.current_assignments:
                        dev.current_assignments.append(team.team_name)
                
                logger.info(f"개발자 {user_id}를 {team.team_name}에 배정")

    def update_phase_progress(self, phase: TeamPhase, progress_percentage: int, status: str = None):
        """단계별 진행률 업데이트"""
        phase_key = f"phase_{phase.value.split('_')[1]}"
        if phase_key in self.team_assignments:
            team = self.team_assignments[phase_key]
            team.progress_percentage = progress_percentage
            if status:
                team.current_status = status
            
            logger.info(f"{team.team_name} 진행률 업데이트: {progress_percentage}% ({status})")

    def get_next_phase_recommendation(self) -> Optional[Dict[str, any]]:
        """다음 단계 추천"""
        current_completed = [
            team for team in self.team_assignments.values() 
            if team.current_status == "완료"
        ]
        
        if len(current_completed) >= 2:  # Phase 0, 1 완료
            return {
                "recommended_phase": TeamPhase.PHASE_2_CANVAS,
                "reasoning": "Phase 0 (기반 구축)과 Phase 1 (WebSearch Hybrid)이 완료되어 Phase 2 (Canvas & Information Gap)을 시작할 수 있습니다.",
                "required_preparation": [
                    "Canvas 시스템 현재 상태 분석",
                    "Information Gap Analyzer 코드 리뷰",
                    "병렬 처리 성능 기준 설정",
                    "팀 리소스 재배정"
                ],
                "estimated_duration": "2.5주",
                "success_criteria": self.phase_requirements[TeamPhase.PHASE_2_CANVAS]["success_criteria"]
            }
        
        return None

    def generate_team_report(self) -> Dict[str, any]:
        """종합 팀 리포트 생성"""
        return {
            "report_generated_at": datetime.now().isoformat(),
            "team_overview": self.get_current_team_status(),
            "phase_details": {
                phase_id: {
                    **team.__dict__,
                    "start_date": team.start_date.isoformat(),
                    "target_completion_date": team.target_completion_date.isoformat()
                }
                for phase_id, team in self.team_assignments.items()
            },
            "developer_profiles": {
                user_id: {
                    **dev.__dict__,
                    "primary_role": dev.primary_role.value,
                    "secondary_roles": [role.value for role in dev.secondary_roles]
                }
                for user_id, dev in self.developers.items()
            },
            "recommendations": {
                "next_phase": self.get_next_phase_recommendation(),
                "team_optimizations": [
                    "Phase 2를 위한 Canvas 전문가 추가 고려",
                    "병렬 처리 성능 테스트 전문가 보강",
                    "사용자 테스트 팀과의 협업 강화"
                ]
            }
        }


# 전역 팀 관리자 인스턴스
team_manager = LangGraphTeamManager()


def get_team_manager() -> LangGraphTeamManager:
    """팀 관리자 인스턴스 반환"""
    return team_manager


def get_current_phase_team() -> Optional[TeamAssignment]:
    """현재 진행 중인 단계의 팀 정보 반환"""
    for team in team_manager.team_assignments.values():
        if team.current_status in ["진행중", "완료"]:
            return team
    return None


def get_developer_workload(user_id: str) -> Dict[str, any]:
    """개발자 업무 부하 조회"""
    dev = team_manager.get_developer_profile(user_id)
    if not dev:
        return {"error": "개발자를 찾을 수 없습니다"}
    
    active_assignments = len(dev.current_assignments)
    workload_percentage = min(100, (active_assignments * 25))  # 최대 4개 배정 = 100%
    
    return {
        "developer": dev.name,
        "active_assignments": active_assignments,
        "workload_percentage": workload_percentage,
        "availability_hours": dev.availability_hours_per_week,
        "specialties": dev.specialties,
        "experience_score": (dev.langgraph_experience + dev.legacy_experience) / 2,
        "recommendations": [
            "적정 업무량" if workload_percentage <= 75 else "업무량 과다 - 재배정 필요",
            f"LangGraph 경험: {dev.langgraph_experience}/10",
            f"Legacy 경험: {dev.legacy_experience}/10"
        ]
    }