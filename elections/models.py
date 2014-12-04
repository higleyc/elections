from django.db import models
from django.contrib.auth.models import User
import rules

class VotingRuleOption(models.Model):
    rule = models.IntegerField("Voting Rule Index", default=0)
    
    def get_rule_class(self):
        if self.rule == 0:
            return rules.PluralityRule
        elif self.rule == 1:
            return rules.PluralityRunoffRule
        elif self.rule == 2:
            return rules.BordaRule
        elif self.rule == 3:
            return rules.STV
        else:
            return None
    
    def __unicode__(self):
        if self.rule == 0:
            return "Plurality"
        elif self.rule == 1:
            return "Plurality Runoff"
        elif self.rule == 2:
            return "Borda"
        elif self.rule == 3:
            return "STV"
        else:
            return "Undefined Rule"

class ElectionRound(models.Model):
    name = models.CharField("Name", max_length = 200)
    description = models.TextField("Description", null=True, blank=True)
    rule = models.ForeignKey(VotingRuleOption)
    vote_on_order = models.BooleanField("Can Vote on Election Order", default=False)
    order_vote_margin = models.FloatField("Order Vote Margin (%)", null=True, blank=True)
    
    def __unicode__(self):
        return self.name

class Candidate(models.Model):
    name = models.CharField("Name", max_length = 200, blank=True, null=True)
    is_user = models.BooleanField("Is a User", default=False)
    user = models.OneToOneField(User, null=True, blank=True, default=None)
    qualified = models.BooleanField("Is Qualified to Run", default=True)
    
    def get_name(self):
        if self.is_user:
            return self.user.first_name + " " + self.user.last_name
        else:
            return self.name
    
    def __unicode__(self):
        return self.get_name()
    
class Election(models.Model):
    name = models.CharField("Name", max_length = 200)
    description = models.TextField("Description", null=True, blank=True)
    election_round = models.ForeignKey(ElectionRound)
    candidates = models.ManyToManyField(Candidate, blank=True, null=True)
    order = models.IntegerField("Election Order Number", default=1)
    
    def has_user_voted(self, user, subround):
        profiles = self.preferenceprofile_set.filter(user=user, subround=subround)
        
        return (len(profiles) > 0)
    
    def __unicode__(self):
        return self.name

class PreferenceProfile(models.Model):
    user = models.ForeignKey(User)
    election = models.ForeignKey(Election)
    subround = models.IntegerField("Election Sub-Round #", default=0)
    
    def __unicode__(self):
        return self.election.name + "-" + str(self.subround) + " (" + self.user.__unicode__() + ")"
    

class Vote(models.Model):
    candidate = models.ForeignKey(Candidate)
    profile = models.ForeignKey(PreferenceProfile)
    rank = models.IntegerField("0-indexed Rank", default=0)
    
    def __unicode__(self):
        return self.profile.election.name + " : " + self.candidate.get_name() + " (" + str(self.rank) + ")"

class ElectionResult(models.Model):
    election = models.ForeignKey(Election)
    conclusive = models.BooleanField("Is Conclusive?")
    winner = models.ForeignKey(Candidate, null=True, blank=True)

class CurrentActivity(models.Model):
    #ACTIVITY IDS
    #0 - pre-start
    #1 - pre do reordering vote
    #2 - do reordering vote open
    #3 - do reordering vote closed
    #4 - reordering vote open
    #5 - post-reordering
    #6 - pre-vote
    #7 - vote open
    #8 - post-vote
    #9 - done
    
    election_round = models.ForeignKey(ElectionRound)
    activity = models.IntegerField("Activity ID", default=0)
    next_activity = models.IntegerField("Next Activity ID", default=0)
    election = models.ForeignKey(Election, null=True, blank=True)
