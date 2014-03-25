from red.activity import Activity
import traceback
from models.model import Match, Player, Team, Base, initSchema

class Creatematch(Activity):
    
    def onCreate(self, data=None):
        self.teamARfid = []
        self.teamBRfid = []
        self.setLayout("match_setup")
        

  
    def receiveRfidinputMessage(self,message):
        if message["head"]=="player_rfid":
            self.loadPlayer(message["data"])
            
  
