#match.py

#Proccess for management of current match

import threading, zmq
from models import Match, Session, Player, Team, Base, initSchema
from sqlalchemy.orm import sessionmaker
from addresses import *


class ControllerProcess (threading.Thread):

    def __init__(self, context=None):
        super(ControllerProcess, self).__init__()
        
        self.is_active = False;
        self.match = Match()
        self.context = context or zmq.Context.instance()

        self.session = Session()

        self.inputSocket = self.context.socket(zmq.PAIR)
        self.inputSocket.bind(getInputSocketAddr())
        self.displaySocket = self.context.socket(zmq.PAIR)
        self.displaySocket.bind(getDisplaySocketAddr())
        self.poller = zmq.Poller()
       

    def run(self):
        while True:
            try:
                poller_socks = dict(self.poller.poll(2))
            except KeyboardInterrupt:
                print("Received Key interrupt. Exiting")
                break

            try:
                message = self.displaySocket.recv_json()
            except zmq.error.ContextTerminated:
                break;

            if message["header"] == "stop":
                self.displaySocket.send_json({"header":"stop"})
                break;
            elif message['header'] == "echo":
                self.inputSocket.send_json({'header':'respond_echo'})
            else:
                self.processMessage(message);


    def is_active(self):
        return self.is_active;


    def processMessage(self,message):
        if message["header"] == "start_match":
            self.start_match(message["data"]["team_a"],message["data"]["team_b"]);
        elif message["header"] == "a_scored":
            self.team_scored("a");
        elif message["header"] == "b_scored":
            self.team_scored("b");
        elif message["header"] == "end_match":
            self.end_match();
        elif message["header"] == "new_player":
            self.new_player(message["data"]["name"]);
        elif message["header"] == "new_team":
            if len(message["data"]["team_name"]) == 0:
                self.new_team(message["data"]["player_a"],message["data"]["player_b"],message["data"]["team_name"]);
            else:
                self.new_team(message["data"]["player_a"],message["data"]["player_b"],message["data"]["player_a"]+'+'+message["data"]["player_b"]);
        else:
            print("We (match) received something (message), but we are unsure what it is")
        print('Match is waiting for input:');


    def start_match(self,teama,teamb):
        if self.is_active:
            print ("Unable to start match, already in progress!")
            return
        team_a = self.session.query(Team).filter(Team.name == teama).one()
        team_b = self.session.query(Team).filter(Team.name == teamb).one()
        print("Match: received a match, starting match between: "+team_a.name+" and "+team_b.name);
        self.is_active = True
        self.match = Match( team_a = team_a, score_a = 0,\
                            team_b = team_b, score_b = 0)
        self.session.add(self.match)


    def end_match(self):
        if not self.is_active:
            print ("Unable to end match, no match in progress!")
            return
        print ("Ending match and saving the results")
        self.is_active = False
        self.session.commit()
        self.match = None


    def team_scored(self, team):
        if not self.is_active:
            print ("No match in progress!")
            return
        if team == 'a':
            scoring_team = self.match.team_a;
            self.match.score_a = self.match.score_a + 1
        elif team == 'b':
            scoring_team = self.match.team_b;
            self.match.score_b = self.match.score_b + 1
        else:
            print ("Who the hell scored")
        print("Some scored it was team: " + scoring_team.name)
        print("Score is now: %s - %s" % (self.match.score_a  ,self.match.score_b))
        # Broadcast to display
        self.displaySocket.send_json(
            {"header":"score_update", 
            "data":{"a":self.match.score_a,
            "b":self.match.score_b}}
            )


    def new_player(self, name):
        self.session.add(Player(name = name))
        self.session.commit()


    def new_team(self, name_a, name_b, team_name):
        team = Team(name = team_name)
        self.session.add(team)
        players = self.session.query(Player).filter(Player.name.in_([name_a,name_b]))
        if players.count() != 2:
            print("Something amiss! Found " + players.count() + " players when expecting 2")
            self.session.rollback()
            return
        for player in players:
            team.players.append(player)
        self.session.commit()
