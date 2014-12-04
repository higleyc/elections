from django.http import HttpResponse, HttpResponseBadRequest
from django.views import generic
from elections.models import *
from django.template import RequestContext, loader
from django.contrib.auth.decorators import login_required
import elections.rules
import logging

logger = logging.getLogger(__name__)

class IndexView(generic.ListView):
    model = ElectionRound
    template_name = "elections/index.html"

class Option:
    id = None
    name = None

def valid_ranking(rankings):
    numbers = {}
    for i in range(1, len(rankings) + 1):
        numbers[i] = False
    for ranking in rankings:
        print ranking
        if ranking[1] <1 or ranking[1] > len(rankings):
            return False
        if numbers[ranking[1]]:
            return False
        numbers[ranking[1]] = True
    
    return True

@login_required
def manage_election(request):
    if not request.user.is_superuser:
        return HttpResponseBadRequest("You are not logged in as an admin")
    
    message = ""
    button_message = ""
    election_round = None
    next_stage = 0
    immediate_refresh = False
    activity = None
    
    # set election round if necessary
    activities = CurrentActivity.objects.all()
    if len(activities) == 0:
        if request.method == "POST":
            election_round = ElectionRound.objects.get(id=int(request.POST.get("round", "")))
            activity = CurrentActivity(election_round=election_round)
        else:
            template = loader.get_template("elections/manage_select_round.html")
            context = RequestContext(request, {
                "round_list" : ElectionRound.objects.all()})
    
            return HttpResponse(template.render(context))
    else:
        activity = activities[0]
        election_round = activity.election_round
    
    if request.method == "POST":
        activity.activity = activity.next_activity
    
    if activity.activity == 0:
        message = "Not yet activated"
        button_message = "Begin"
        if election_round.vote_on_order:
            activity.next_activity = 1
        else:
            activity.next_activity = 6
            content = "Election order voting disabled; using preset order:\n"
            elections = Election.objects.filter(election_round=election_round).order_by("order")
            for election in elections:
                content += " "
                content += election.name
                content += ","
            content = content[:-1]
            event = Event(election_round=election_round,content=content)
            event.save()
    elif activity.activity == 1:
        message = "Ready to start ordering change voting"
        button_message = "Start ordering voting"
        activity.next_activity = 2
        
        # set up temp elections
        er_tmp = ElectionRound(name="TMP Order", rule=VotingRuleOption.objects.get(rule=0))
        er_tmp.save()
        election_yesno = Election(name="Change election order", election_round=er_tmp)
        election_order = Election(name="Election order", election_round=er_tmp)
        election_yesno.save()
        election_order.save()
        candidate_yes = Candidate(name="Yes")
        candidate_yes.save()
        candidate_no = Candidate(name="No")
        candidate_no.save()
        election_yesno.candidates.add(candidate_yes)
        election_yesno.candidates.add(candidate_no)
        for election in election_round.election_set.all():
            candidate = Candidate(name=election.name)
            candidate.save()
            election_order.candidates.add(candidate)
        
    elif activity.activity == 2:
        message = "Vote on changing election order open"
        button_message = "Close voting"
        activity.next_activity = 3
    elif activity.activity == 3:
        # determine if the vote passed
        er_tmp = ElectionRound.objects.get(name="TMP Order")
        election = er_tmp.election_set.get(name="Change election order")
        plurality = rules.PluralityRule(election)
        profiles = PreferenceProfile.objects.filter(election=election)
        plurality.execute_round(profiles)
        yes_votes = plurality.result_vector[election.candidates.get(name="Yes")]
        no_votes = plurality.result_vector[election.candidates.get(name="No")]
        result = ElectionResult(election=election, conclusive=True)
        percent = float(yes_votes) / (yes_votes + no_votes)
        if percent < election_round.order_vote_margin / 100:
            activity.activity = 6
            activity.save()
            result.winner = election.candidates.get(name="No")
            result.save()
            event = Event(election_round=election_round,content="Vote to change election order failed")
            event.save()
            for election in er_tmp.election_set.all():
                for candidate in election.candidates.all():
                    candidate.delete()
                election.delete()
            er_tmp.delete()
            immediate_refresh = True
        else:
            result.winner = election.candidates.get(name="Yes")
            result.save()
            event = Event(election_round=election_round,content="Vote to change election order passed")
            event.save()
            message = "Ready to start ordering voting"
            button_message = "Start voting"
            activity.next_activity = 4  
    elif activity.activity == 4:
        message = "Vote on election order open"
        button_message = "Close voting"
        activity.next_activity = 5
    elif activity.activity == 5:
        # calculate results and temp object cleanup
        if election_round.vote_on_order:
            #only perform if the vote actually passed
            er_tmp = ElectionRound.objects.get(name="TMP Order")
            election = er_tmp.election_set.get(name="Change election order")
            result = ElectionResult.objects.get(election=election)
            if result.winner.name == "Yes":
                election = er_tmp.election_set.get(name="Election order")
                borda = rules.BordaRule(election)
                profiles = PreferenceProfile.objects.filter(election=election)
                borda.execute_round(profiles)
                content = "Determined voting order:\n "
                for i in range(len(borda.sorted_results)):
                    #FIXME: problem if nonunique names
                    result = borda.sorted_results[i]
                    this_election = Election.objects.get(name=result[0].name)
                    content += " "
                    content += this_election.name
                    content += ","
                    this_election.order = i + 1
                    this_election.save()
                content = content[:-1]
                event = Event(election_round=election_round,content=content)
                event.save()
            
            #cleanup
            for election in er_tmp.election_set.all():
                for candidate in election.candidates.all():
                    candidate.delete()
                election.delete()
            er_tmp.delete()
            
            activity.activity = 6
            immediate_refresh = True
    elif activity.activity == 6:
        # pre-vote
        if activity.election == None:
            activity.election = Election.objects.filter(election_round=election_round).get(order=1)
            message = "Ready to vote on " + activity.election.__unicode__()
            button_message = "Start voting"
            activity.next_activity = 7
        else:
            elections = Election.objects.filter(election_round=election_round).filter(order=(activity.election.order + 1))
            if len(elections) == 0:
                message = "Elections done!"
                message_button = "Finish"
                activity.next_activity = 9
            else:
                activity.election = elections[0]
                message = "Ready to vote on " + activity.election.__unicode__()
                button_message = "Start voting"
                activity.next_activity = 7
    elif activity.activity == 7:
        # vote open
        message = "Voting on " + activity.election.__unicode__()
        button_message = "Close voting"
        activity.next_activity = 8
    elif activity.activity == 8:
        # post-vote - do voting results
        election = activity.election
        rule_class = election_round.rule.get_rule_class()
        mechanism = rule_class(election)
        profiles = PreferenceProfile.objects.filter(election=election)
        if mechanism.execute_round(profiles):
            after_elections = Election.objects.filter(election_round=election_round).filter(order__gt=election.order)
            for after_election in after_elections:
                after_election.order += 1
                after_election.save()
            subelection = Election(name=(election.name + " - Next round"),
                                   election_round=election_round,
                                   order=(election.order + 1))
            subelection.save()
            for candidate in mechanism.curr_candidates:
                subelection.candidates.add(candidate)
            subelection.save()
            event = Event(election_round=election_round,content=("Election for %s requires an additional round" % election.name))
            event.save()
        else:
            results = ElectionResult(election=election)
            winner = mechanism.get_winner()
            if winner == False:
                results.conclusive = False
                event = Event(election_round=election_round,content=("Election for %s was inconclusive" % election.name))
                event.save()
            else:
                results.conclusive= True
                results.winner = winner
                event = Event(election_round=election_round,content=("Election for %s concluded; the winner is %s" % (election.name, winner.get_name())))
                event.save()
                # exclude winner
                winner.qualified = False
                for election in Election.objects.filter(election_round=election_round):
                    if len(election.candidates.filter(id=winner.id)) > 0:
                        election.candidates.remove(winner)
            results.save()
            
            
        
        activity.activity = 6
        immediate_refresh = True
        
    elif activity.acitvity == 9:
        # all voting done
        message = "You're all done"
        event = Event(election_round=election_round,content="All elections complete")
        event.save()
        
    
    activity.save()
    
    template = loader.get_template("elections/manage.html")
    context = RequestContext(request, {
        "button_message" : button_message,
        "next_stage" : next_stage,
        "selected_round" : election_round,
        "status_message" : message,
        "round_list" : ElectionRound.objects.all(),
        "immediate_refresh" : immediate_refresh})
    
    return HttpResponse(template.render(context))

@login_required
def vote(request):
    user = request.user
    status = ""
    is_voting = False
    voting_full_rank = False
    voting_question = ""
    election_id = -1
    options = []
    option_names = []
    events = []
    
    
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
    
    
    activities = CurrentActivity.objects.all()
    if len(activities) == 0:
        status = "Elections are not yet active"
    else:
        activity = activities[0]
        election_round = activity.election_round
        if request.method == "POST":
            if activity.activity == 2:
                # receiving do reordering vote
                er_tmp = ElectionRound.objects.get(name="TMP Order")
                election = er_tmp.election_set.get(name="Change election order")
                if election.has_user_voted(user, 0):
                    return HttpResponseBadRequest("You have already voted")
                choice = Candidate.objects.filter(id=request.POST.get("ballot", ""))
                if len(choice) == 0:
                    return HttpResponseBadRequest("Invalid vote")
                choice = choice[0]
                profile = PreferenceProfile(user=user, election=election)
                profile.save()
                vote = Vote(candidate=choice, profile=profile)
                vote.save()
                status = "Vote cast"
            elif activity.activity == 4:
                # receiving reordering vote
                er_tmp = ElectionRound.objects.get(name="TMP Order")
                election = er_tmp.election_set.get(name="Election order")
                if election.has_user_voted(user, 0):
                    return HttpResponseBadRequest("You have already voted")
                rankings = []
                for candidate in election.candidates.all():
                    rank = request.POST.get("ballot_" + str(candidate.id), "")
                    rankings.append((candidate, int(rank)))
                if not valid_ranking(rankings):
                    return HttpResponseBadRequest("Invalid ranking")
                profile = PreferenceProfile(user=user, election=election)
                profile.save()
                for ranking in rankings:
                    vote = Vote(candidate=ranking[0], profile=profile, rank=int(ranking[1]))
                    vote.save()
                status = "Vote cast"
            elif activity.activity == 7:
                # receiving regular vote
                election = activity.election
                if election.has_user_voted(user, 0):
                    return HttpResponseBadRequest("You have already voted")
                if election_round.rule.get_rule_class().requires_full_rank:
                    rankings = []
                    for candidate in election.candidates.all():
                        rank = request.POST.get("ballot_" + str(candidate.id), "")
                        rankings.append((candidate, int(rank)))
                    if not valid_ranking(rankings):
                        return HttpResponseBadRequest("Invalid ranking")
                    profile = PreferenceProfile(user=user, election=election)
                    profile.save()
                    for ranking in rankings:
                        vote = Vote(candidate=ranking[0], profile=profile, rank=int(ranking[1]))
                        vote.save() 
                else:
                    profile = PreferenceProfile(user=user, election=election)
                    profile.save()
                    choice = Candidate.objects.filter(id=request.POST.get("ballot", ""))
                    if len(choice) == 0:
                        return HttpResponseBadRequest("Invalid vote")
                    choice = choice[0]
                    vote = Vote(candidate=choice, profile=profile)
                    vote.save()
                status = "Vote cast"
        else:
            if activity.activity == 0:
                # Pre-start
                status = "Nothing is happening yet - please wait"
            elif activity.activity == 1:
                # pre do reordering vote
                status = "Nothing is happening yet - please wait"
            elif activity.activity == 2:
                # do reordering vote open
                er_tmp = ElectionRound.objects.get(name="TMP Order")
                election = er_tmp.election_set.get(name="Change election order")
                if election.has_user_voted(user, 0):
                    status = "Vote cast"
                else:
                    status = "Election reordering vote"
                    is_voting = True
                    voting_question = "Should the current election order be changed?"
                    options = election.candidates.all()
                    election_id = election.id
            elif activity.activity == 3:
                # do reordering vote closed
                status = "Election reordering vote done"
            elif activity.activity == 4:
                # reordering vote open
                er_tmp = ElectionRound.objects.get(name="TMP Order")
                election = er_tmp.election_set.get(name="Election order")
                if election.has_user_voted(user, 0):
                    status = "Vote cast"
                else:
                    status = "Election reordering vote"
                    is_voting = True
                    voting_full_rank = True
                    voting_question = "Rank the elctions in the order in which they should be voted on (1 first)"
                    options = election.candidates.all()
                    election_id = election.id
            elif activity.activity == 5:
                # reordering vote closed
                status = "Election reordering vote done"
            elif activity.activity == 6:
                # pre-vote
                status = "Waiting to vote"
            elif activity.activity == 7:
                # vote open
                election = activity.election
                if election.has_user_voted(user, 0):
                    status = "Vote cast"
                else:
                    status = "Vote on " + election.name
                    is_voting = True
                    voting_full_rank = election_round.rule.get_rule_class().requires_full_rank
                    voting_question = "Indicate your preference on the following candidates"
                    options = election.candidates.all()
                    election_id = election.id
            elif activity.activity == 8:
                # post-vote
                status = "Please wait"
            elif activity.activity == 9:
                # voting done
                status = "All elections complete"
        events = Event.objects.filter(election_round=election_round).order_by("-timestamp")
    
    full_options = []        
    for option in options:
        o = Option()
        o.id = option.id
        o.name = option.get_name()
        full_options.append(o)
    if len(events) > 10:
        events = events[:10]
    
    if is_voting and (not voting_full_rank):
        template = loader.get_template("elections/choice_vote.html")
    elif is_voting and voting_full_rank:
        template = loader.get_template("elections/rank_vote.html")
    else:
        template = loader.get_template("elections/vote_base.html")
    context = RequestContext(request, {
        "voting_status" : status,
        "voting_question" : voting_question,
        "options" : full_options,
        "option_names" : option_names,
        "election_id" : election_id,
        "events" : events,
        "is_voting" : is_voting
    })
    
    return HttpResponse(template.render(context))
