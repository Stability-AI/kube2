from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class Cluster(object):
    name: str
    created_at: datetime
    status: str


@dataclass
class Context(object):
    name: str
    selected: bool


@dataclass
class Volume(object):
    name: str
    capacity: str
    usage: str
    created: datetime
    attached_to_jobs: List[str]
