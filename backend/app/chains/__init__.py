# 导入模块化链组件
from .base_chains import base_chain_manager
from .planning_chains import planning_chains
from .analysis_chains import analysis_chains
from .report_chains import report_chains

# 保持向后兼容
from .research_chains import research_chains

__all__ = [
    "base_chain_manager",
    "planning_chains", 
    "analysis_chains",
    "report_chains",
    "research_chains"
]