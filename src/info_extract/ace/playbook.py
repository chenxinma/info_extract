from pathlib import Path
from pydantic import BaseModel, Field
import os

class Playbook(BaseModel):
    bullet_id: str = Field(description="文件序号")
    content: str = Field(description="策略条目内容")

class PlaybookManager:
    def __init__(self, playbook_dir: str, preffix:str):
        self.playbook_dir = Path(playbook_dir)
        self.preffix = preffix
        self.count = 0
        self.list_playbooks()
    
    def list_playbooks(self) -> list[str]:
        playbooks = []
        for f in self.playbook_dir.glob(f"{self.preffix}*.txt"):
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read()
                playbooks.append(content)
                idx = int(f.stem.split("_")[1])
                if idx > self.count:
                    self.count = idx
        return playbooks
    
    def overview_playbooks(self) -> list[Playbook]:
        playbooks = []
        for f in self.playbook_dir.glob(f"{self.preffix}*.txt"):
            with open(f, "r", encoding="utf-8") as fp:
                content = fp.read()
                playbooks.append(Playbook(bullet_id=f.stem, content=content))
        return playbooks
    
    def create_playbook(self, content):
        fname = f"{self.preffix}_{self.count+1:05d}.txt"
        with open(self.playbook_dir / fname, "w", encoding="utf-8") as fp:
            fp.write(content)
    
    def modify_playbook(self, bullet_id:str, new_content:str):
        fname = f"{bullet_id}.txt"
        with open(self.playbook_dir / fname, "w", encoding="utf-8") as fp:
            fp.write(new_content)
    
    def delete_playbook(self, bullet_id:str):
        fname = f"{bullet_id}.txt"
        f = self.playbook_dir / fname
        os.remove(f)