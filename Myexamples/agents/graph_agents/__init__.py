from .scholar_scour import get_scholar_scour_config
from .qwen_leader import get_qwen_leader_config
from .qwen_editor import get_qwen_editor_config
from .idea_igniter import get_idea_igniter_config
from .local_rag import run_local_rag

# 新增的4个智能体模块
from .prof_qwen_ethics import get_prof_qwen_ethics_config
from .dr_qwen_technical import get_dr_qwen_technical_config
from .dr_qwen_practical import get_dr_qwen_practical_config
from .critic_crucible import get_critic_crucible_config

__all__ = [
    "get_scholar_scour_config",
    "get_qwen_leader_config",
    "get_qwen_editor_config",
    "get_idea_igniter_config",
    "run_local_rag",
    # 新增的智能体配置函数
    "get_prof_qwen_ethics_config",
    "get_dr_qwen_technical_config", 
    "get_dr_qwen_practical_config",
    "get_critic_crucible_config",
]


