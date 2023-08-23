from __future__ import annotations

'''
    This file contains the class for the Kasumi SDK.
    It is used to interact with the Kasumi API.
'''
from typing import List, Dict, Any, Iterator, Tuple
from .abstract import *
from .embedding import KasumiEmbedding

import threading

class KasumiConfigration(AbstractKasumiConfigration):
    _token: str = ""
    _search_key: str = ""
    _kasumi_url: str = ""
    _app_id: int = 0
    _search_desc : str = ""
    _search_strategy: AbstractKasumiSearchStrategy  

    def __init__(self, app_id: int, token: str, search_key: str, search_desc: str, 
                  search_strategy: AbstractKasumiSearchStrategy,
                  kasumi_url: str = "http://kasumi.miduoduo.org:8192"):
        self._app_id = app_id
        self._token = token
        self._search_key = search_key
        self._search_strategy = search_strategy
        self._kasumi_url = kasumi_url
        self._search_desc = search_desc

    def get_app_id(self) -> int:
        return self._app_id

    def get_token(self) -> str:
        return self._token
    
    def get_search_key(self) -> str:
        return self._search_key
    
    def get_kasumi_url(self) -> str:
        return self._kasumi_url
    
    def get_search_strategy(self) -> AbstractKasumiSearchStrategy:
        return self._search_strategy
    
    def get_search_desc(self) -> str:
        return self._search_desc

class KasumiSearchResultField(AbstractKasumiSearchResultField):
    """
    KasumiSearchResultField is used to represent a field in the search result.
    _key: The key of the field.
    _content: The content of the field.
    _llm_disabled: this field will not be sent to the LLM if this is set to True.
    _show_disabled: this field will not be shown to the client if this is set to True.
    """
    _key: str = ""
    _content: str = ""
    _llm_disabled: bool = False
    _show_disabled: bool = False

    def __init__(self,key: str, content: str, llm_disabled: bool = False, show_disabled: bool = False):
        self._key = key
        self._content = content
        self._llm_disabled = llm_disabled
        self._show_disabled = show_disabled

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self._key,
            "content": self._content,
            "llm_disabled": self._llm_disabled
        }

class KasumiSearchResult(AbstractKasumiSearchResult):
    _fields: List[KasumiSearchResultField] = []

    def __init__(self, fields: List[KasumiSearchResultField]):
        self._fields = fields

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fields": [field.to_dict() for field in self._fields]
        }
    
    @staticmethod
    def load_from_dict(data: Dict[str, Any], disabled_llm_columns: List[str] = None, disabled_show_columns: List[str] = None) -> KasumiSearchResult:
        disabled_llm_columns = disabled_llm_columns or []
        disabled_show_columns = disabled_show_columns or []

        fields = []
        for key, value in data:
            fields.append(KasumiSearchResultField(
                key=key, content=value, llm_disabled=key in disabled_llm_columns, show_disabled=key in disabled_show_columns
            ))

        return KasumiSearchResult(fields)

class DefaultSearchStrategy(AbstractKasumiSearchStrategy):
    '''
    This class is used to implement the default search strategy.
    '''

    def on_single_result(result: List[KasumiSearchResult]) -> Tuple[bool, List[KasumiSearchResult]]:
        '''
            on single result,return processed single_result and complete search
            for simple scenario, can just judge if result empty
            for complex scenario, can judge if result is what we want using LLM or other method
        '''
        if len(result) == 0:
            return False,result
        else:
            return True,result
        
    def on_all_result(result: List[List[KasumiSearchResult]]) -> List[KasumiSearchResult]:
        '''
            on all result, maybe we can do some post process here
            for simple scenario, can just return first non-empty result
            for complex scenario, can do some post process here,eg: using LLM to summarize or other things
        '''
        temp_result = None
        for i in result:
            if len(i) != 0:
                temp_result = i
                break
        return temp_result

    def search(app: 'Kasumi', search_param: Dict) -> List[KasumiSearchResult]:
        spiders = sorted(app.get_spiders(), key=lambda spider: spider.priority, reverse=True)
        all_results = []
        for spider in spiders:
            single_result = spider.search(search_param)
            complete,single_result = DefaultSearchStrategy.on_single_result(single_result)
            all_results.extend(single_result)
            if complete:
                break
        return DefaultSearchStrategy.on_all_result(all_results)

class KasumiSearchResponse(AbstractKasumiSearchResponse):
    _code: int = 0
    _message: str = ""
    _data: List[KasumiSearchResult]

    def __init__(self, code: int, message: str, data: List[KasumiSearchResult]):
        self._code = code
        self._message = message
        self._data = data

    def get_code(self) -> int:
        return self._code

    def get_message(self) -> str:
        return self._message

    def get_data(self) -> List[KasumiSearchResult]:
        return self._data
    
    def __str__(self) -> str:
        return f"KasumiSearchResponse(code={self._code},message={self._message},data={self._data})"

class KasumiInfoResponse(AbstractKasumiInfoResponse):
    _code: int = 0
    _message: str = ""
    _data: Dict[str, Any]

    def __init__(self, code: int, message: str, data: Dict[str, Any]):
        self._code = code
        self._message = message
        self._data = data

    def get_code(self) -> int:
        return self._code

    def get_message(self) -> str:
        return self._message

    def get_data(self) -> Dict[str, Any]:
        return self._data

class KasumiSession(AbstractKasumiSession):
    _user_token: str = ""

class Kasumi(AbstractKasumi):
    """
    This class is used to interact with the Kasumi API.

    :param config: The configuration of the Kasumi SDK.
    
    :raises all methods in Kasumi may raise KasumiException if the Kasumi API returns an error.
    """
    _config: KasumiConfigration = None
    _spiders: List[AbstractKasumiSpider] = []
    _sessions: Dict[int, KasumiSession] = {}
    _embedding: AbstractKasumiEmbedding = KasumiEmbedding()

    def __init__(self, config: KasumiConfigration):
        self._config = config

    def embeding_text(self, text: str) -> List[float]:
        ident = threading.get_ident()
        try:
            if ident in self._sessions:
                session = self._sessions[threading.get_ident()]
                embedding = self._embedding.embedding_text(self, text, TokenType.ENCRYPTION, session._user_token)
            else:
                embedding = self._embedding.embedding_text(self, text, TokenType.PLAINTEXT, self._config.get_token())
            return embedding
        except Exception as e:
            raise KasumiException("Failed to get embedding of text. for more information, please see the traceback. %s" % e)
        
    def search_embedding_similarity(self, embedding: List[float], limit: int = 10) -> List[AbstractKasumiEmbeddingItem]:
        ident = threading.get_ident()
        try:
            if ident in self._sessions:
                session = self._sessions[threading.get_ident()]
                similarities = self._embedding.search_similarity(self, embedding, TokenType.ENCRYPTION, session._user_token, limit=limit)
            else:
                similarities = self._embedding.search_similarity(self, embedding, TokenType.PLAINTEXT, self._config.get_token(), limit=limit)
            return similarities
        except Exception as e:
            raise KasumiException("Failed to search embedding similarity. for more information, please see the traceback. %s" % e)

    def get_embedding_by_id(self, id: str) -> AbstractKasumiEmbeddingItem:
        ident = threading.get_ident()
        try:
            if ident in self._sessions:
                session = self._sessions[threading.get_ident()]
                embedding = self._embedding.get_embedding_by_id(self, id, TokenType.ENCRYPTION, session._user_token)
            else:
                embedding = self._embedding.get_embedding_by_id(self, id, TokenType.PLAINTEXT, self._config.get_token())
            return embedding
        except Exception as e:
            raise KasumiException("Failed to get embedding by id. for more information, please see the traceback. %s" % e)

    def insert_embedding(self, embedding: List[float], id: str) -> bool:
        try:
            return self._embedding.insert_embedding(self, embedding, id)
        except Exception as e:
            raise KasumiException("Failed to insert embedding. for more information, please see the traceback. %s" % e)

    def add_spider(self, spider: AbstractKasumiSpider) -> None:
        self._spiders.append(spider)

    def get_spiders(self) -> List[AbstractKasumiSpider]:
        return self._spiders

    def _handle_request_info(self, request: Dict[str, Any]) -> KasumiInfoResponse:
        if request.get('remote_search_key') != self._config.get_search_key():
            return KasumiInfoResponse(
                code=401, message="Unauthorized", data={}
            )

        return KasumiInfoResponse(
            code=200, message="OK", data={
                "search_desc": self._config.get_search_desc(),
            }
        )

    def _handle_request_search(self, request: Dict[str, Any]) -> KasumiSearchResponse:
        if request.get('remote_search_key') != self._config.get_search_key():
            return KasumiSearchResponse(
                code=401, message="Unauthorized", data=[]
            )

        ident = threading.get_ident()
        self._sessions[ident] = KasumiSession()

        search_param = request.get('search_param')
        results = self._config.get_search_strategy().search(self,search_param)

        if ident in self._sessions:
            del self._sessions[ident]

        return KasumiSearchResponse(
            code=200, message="OK", data=results
        )

    def run_forever(self) -> None:
        pass