import operator

class VotingRule:
    active_round = 0
    requires_full_rank = None
    
    def __init__(self, election):
        self.election = election
        self.init_candidates = election.candidates.all()
        self.curr_candidates = self.init_candidates
    
    # True if more rounds required, False otherwise
    def execute_round(self, election, profiles):
        pass
    
    # Returns the winning candidate if one was determined, False otherwise
    def get_winner(self):
        pass

def calculate_scores(score_vector, candidates, profiles):
    result = dict()
    for candidate in candidates.all():
        result[candidate] = 0
    
    for profile in profiles:
        votes = profile.vote_set.all().order_by('rank')
        for i in range(len(votes)):
            result[votes[i].candidate] += score_vector[i]
    
    return result

class BordaRule(VotingRule):
    requires_full_rank = True
    sorted_results = list()
    
    def get_score_vector(self, n):
        vector = list()
        for i in reversed(range(0, n)):
            vector.append(i)
        
        return vector
    
    def execute_round(self, profiles):
        result_vector = calculate_scores(
            self.get_score_vector(len(self.curr_candidates.all())),
            self.curr_candidates, profiles)
        self.sorted_results = list(reversed(sorted(result_vector.items(),
                                     key=operator.itemgetter(1))))
        
        print "Borda results:"
        for result in self.sorted_results:
            print "\t%s: %i" % (result[0].name, result[1])
        
        return False
    
    def get_winner(self):
        if len(self.sorted_results) > 1 and \
            self.sorted_results[0][1] == self.sorted_results[1][1]:
            return False
        else:
            return self.sorted_results[0][0]
    
class PluralityRule(VotingRule):
    requires_full_rank = False
    sorted_results = list()
    result_vector = dict()
    
    def get_score_vector(self, n):
        vector = list()
        vector.append(1)
        for i in range(1, n):
            vector.append(0)
        
        return vector
    
    def execute_round(self, profiles):
        self.result_vector = calculate_scores(
            self.get_score_vector(len(self.curr_candidates.all())),
            self.curr_candidates, profiles)
        self.sorted_results = list(reversed(sorted(self.result_vector.items(),
                                key=operator.itemgetter(1))))
        
        return False
    
    def get_winner(self):
        if len(self.sorted_results) == 0:
            return False
        if len(self.sorted_results) > 1 and \
            self.sorted_results[0][1] == self.sorted_results[1][1]:
            return False
        else:
            return self.sorted_results[0][0]
    
class PluralityRunoffRule(PluralityRule):
    def execute_round(self, profiles):
        result_vector = calculate_scores(
            self.get_score_vector(len(self.curr_candidates)),
            self.curr_candidates, profiles)
        self.sorted_results = list(reversed(sorted(result_vector.items(),
                                key=operator.itemgetter(1))))
        if len(self.sorted_results) > 2 and \
            float(self.sorted_results[0][1]) / len(profiles) < 0.5:
            self.curr_candidates = list()
            self.curr_candidates.append(self.sorted_results[0][0])
            self.curr_candidates.append(self.sorted_results[1][0])
            self.active_round += 1
            return True
        
        return False

class STV(VotingRule):
    requires_full_rank = False
    winner = None
    
    def execute_round(self, profiles):
        mod_profiles = list()
        for profile in profiles:
            #sorted from first to last?
            mod_profiles.append(profile.vote_set.all())
        
        while len(self.curr_candidates) > 1:
            #calculate votes
            scores = dict()
            for candidate in self.curr_candidates:
                scores[candidate] = 0
            for votes in mod_profiles:
                scores[votes[0].candidate] += 1
            
            #sort candidates
            scores = list(reversed(sorted(scores, key=operator.itemgetter(1))))
            
            #if bottom two are equal we fail
            if scores[-1][1] == scores[-2][1]:
                winner = False
                return False
            
            #remove the loser
            drop = scores[-1][0]
            self.curr_candidates.remove(drop)
            for votes in mod_profiles:
                for i in range(len(votes)):
                    if votes[i].candidate == drop:
                        del votes[i]
                        break
        
        winner = self.curr_candidates[0]
        
        return False
    
    def get_winner(self):
        return winner
