import abc
import datetime
import uuid

import ujson


class AgendaBase(metaclass=abc.ABCMeta):

    @classmethod
    @abc.abstractmethod
    def load_from_json(cls, str: str):
        return NotImplemented

    @abc.abstractmethod
    def get_type(self):
        return NotImplemented

    @abc.abstractmethod
    def get_name(self):
        return NotImplemented

    @abc.abstractmethod
    def set_name(self, agenda_name: str):
        return NotImplemented

    @abc.abstractmethod
    def to_html_dict(self):
        return NotImplemented

    @abc.abstractmethod
    def to_json(self):
        return NotImplemented

    @abc.abstractmethod
    def next_agenda(self):
        return NotImplemented

    @abc.abstractmethod
    def get_agenda_4_frontend(self):
        return NotImplemented


class TextAgenda(AgendaBase):

    @classmethod
    def load_from_json(cls, str: str):
        pass

    def __init__(self):
        self._id = uuid.uuid4().hex
        self._type = 'text'
        self._name = ''
        self._data = {}

    def get_type(self):
        return self._type

    def get_name(self):
        return self._name

    def get_text_id(self):
        return self._id

    def set_name(self, agenda_name: str):
        self._name = agenda_name
        self._update()

    def _update(self):
        self._data = {
            "type": self._type,
            "name": self._name,
        }

    def to_html_dict(self):
        return self._data

    def to_json(self):
        return ujson.dumps(self._data)

    def next_agenda(self):
        return datetime.datetime.now()

    def get_agenda_4_frontend(self):
        return {
            "text_id": self._id
        }


class IVote(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def vote_init(self, options, duration: int, free: bool):
        return NotImplemented

    @abc.abstractmethod
    def get_vote_name(self):
        return NotImplemented

    @abc.abstractmethod
    def update_vote_count(self, member_id: int, vote_option_index: int):
        return NotImplemented

    @abc.abstractmethod
    def get_vote_options(self):
        return NotImplemented
