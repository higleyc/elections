import operator

class VotingRule:
    active_round = 0
    requires_full_rank = None
    
    def __init__(self, election):
        self.election = election
        self.init_candidates = election.candidates
        self.curr_candidates = self.init_candidates
    
    # True if more rounds required, False otherwise
    def execute_round(self, election, profiles):
        pass
    
    # Returns the winning candidate if one was determined, False otherwise
    def get_winner(self):
        pass

def calculate_scores(score_vector, candidates, profiles):
    result = dict()
    for candidate in candidates:
        result[candidate] = 0
    
    for profile in profiles:
        votes = profile.vote_set.objects.order_by('rank')
        for i in range(len(votes)):
            result[votes[i].candidate] += score_vector[i]
    
    return result
    
class PluralityRule(VotingRule):
    requires_full_rank = False
    sorted_results = list()
    
    def get_score_vector(self, n):
        vector = list()
        vector.append(1)
        for i in range(1, n):
            vector.append(0)
        
        return vector
    
    def execute_round(self, profiles):
        result_vector = calculate_scores(
            self.get_score_vector(len(self.curr_candidates)),
            self.curr_candidates, profiles)
        self.sorted_results = sorted(result_vector.items(),
                                key=operator.itemgetter(1))
        
        return False
    
    def get_winner(self):
        if len(self.sorted_results) > 1 and \
            self.sorted_results[0][0] == self.sorted_results[1][0]:
            return False
        else:
            return self.sorted_results[0][0]
    
class PluralityRunoffRule(PluralityRule):
    def execute_round(self, profiles):
        result_vector = calculate_scores(
            self.get_score_vector(len(self.curr_candidates)),
            self.curr_candidates, profiles)
        self.sorted_results = sorted(result_vector.items(),
                                key=operator.itemgetter(1))
        if len(self.sorted_results) > 2 and \
            self.sorted_results[0][1] / len(self.sorted_results) < 0.5:
            self.curr_candidates = list()
            self.curr_candidates[0] = self.sorted_results[0][0]
            self.curr_candidates[1] = self.sorted_results[1][0]
            active_round += 1
            return True
        
        return False
