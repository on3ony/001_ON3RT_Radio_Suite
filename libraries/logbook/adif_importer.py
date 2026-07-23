
"""
ON3RT Radio Suite
Robust ADIF Importer
"""
from pathlib import Path
from typing import List, Dict
import re

class ADIFImporter:
    def __init__(self):
        self.records: List[Dict[str,str]]=[]

    def clear(self):
        self.records.clear()

    def load(self, filename:str)->List[Dict[str,str]]:
        self.clear()
        raw=Path(filename).read_bytes()
        text=None
        for enc in ("utf-8","cp1252","latin1"):
            try:
                text=raw.decode(enc)
                break
            except UnicodeDecodeError:
                pass
        if text is None:
            text=raw.decode("latin1","ignore")
        m=re.search(r"<EOH>",text,re.I)
        if m:
            text=text[m.end():]
        tag=re.compile(r"<([^:>]+):(\d+)(?::[^>]+)?>",re.I)
        for part in re.split(r"<EOR>",text,flags=re.I):
            part=part.strip()
            if not part:
                continue
            rec={}
            pos=0
            while True:
                t=tag.search(part,pos)
                if not t:
                    break
                field=t.group(1).upper().strip()
                n=int(t.group(2))
                start=t.end()
                rec[field]=part[start:start+n]
                pos=start+n
            if rec:
                self.records.append(rec)
        return self.records

    def count(self)->int:
        return len(self.records)

    def get_records(self):
        return self.records.copy()
