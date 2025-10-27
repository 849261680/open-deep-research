from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.llms.deepseek_llm import DeepSeekLLM


class BaseChainManager:
    """基础链管理器 - 提供共用的工具和配置"""

    def __init__(self) -> None:
        self.llm = DeepSeekLLM()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )

    def process_search_results(
        self, results: dict[str, list[dict[str, object]]]
    ) -> list[Document]:
        """处理搜索结果为文档"""
        documents = []
        for source, items in results.items():
            for item in items:
                content = f"标题: {item.get('title', '')}\n"
                content += f"来源: {source}\n"
                content += f"链接: {item.get('link', '')}\n"
                content += f"内容: {item.get('snippet', '')}\n"

                doc = Document(
                    page_content=content,
                    metadata={
                        "source": source,
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                    },
                )
                documents.append(doc)
        return documents


# 全局实例
base_chain_manager = BaseChainManager()
