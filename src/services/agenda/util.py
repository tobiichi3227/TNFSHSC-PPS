from typing import List, Dict


class Vote(object):
    def __init__(self):
        self.is_free_vote: bool = False
        self.completed: bool = False
        self.vote_options: List = []
        self.already_voted: Dict[int | int] = {}
        self.is_start = False
        self.is_end = False

    def add_vote_option(self, option: str):
        self.vote_options.append({
            "option": option,
            "count": 0,
        })

    def update_vote_count(self, member_id: int, vote_option_index: int):
        member_id = int(member_id)
        vote_option_index = int(vote_option_index)

        if member_id in self.already_voted:
            return False

        self.already_voted[member_id] = vote_option_index
        self.vote_options[vote_option_index]['count'] += 1

        return True

    def get_vote_options(self):
        return self.vote_options

    def vote_completed(self):
        self.completed = True

    def set_free_vote(self, flag):
        self.is_free_vote = flag
