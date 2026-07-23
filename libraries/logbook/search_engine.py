"""
ON3RT Radio Suite
Module Logbook
Search Engine
"""

from apps.logbook.repository import LogbookRepository

class SearchEngine:
    def __init__(self):
        self.repository=LogbookRepository()

    def search(self,text:str):
        text=text.strip()
        if not text:
            return self.repository.get_all()
        return self.repository.search(text)

    def close(self):
        self.repository.close()
