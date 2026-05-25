from belote.core.card import Card
import random

numbers = [80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 135, 140, 145, 150, 155, 160, 250, 500]
suits = ["K", "P", "C", "T", "SA", "TA"]

class Bidding:
    def __init__(self, suit, points):
        self.suit = suit
        self.points = points
        self.coinche = False
        self.surcoinche = False
        self.current_player = 0 
    def __str__(self):
        return f"suit:{self.suit}, points:{self.points}, coinche:{self.coinche},surcoinche{self.surcoinche}"
    

def run_bidding():
    valid_numbers = numbers.copy()
    passe = 0
    contracts = []

    
    choice = random.choice(["pass", "bid"])
    if choice == "pass":
        contracts.append("pass")
    else:
        suit = random.choice(suits)
        points = random.choice(numbers)
        contracts.append(Bidding(suit,points))
    #print("joueurs ", 0, ":", contracts[0])
    while passe < 3:
        valid_numbers = valid_bidding(contracts, valid_numbers)
        if len(valid_numbers) == 0:
            choice = "pass"
        else:
            choice = random.choice(["pass", "bid"])
        
        if choice == "pass":
            contracts.append("pass")
            passe+=1
        else:
            suit = random.choice(suits)
            points = random.choice(valid_numbers)
            contracts.append(Bidding(suit,points))
            passe=0
        #print("joueurs ", (len(contracts)-1)%4, ":", contracts[-1])
    if len(contracts) == 4:
        if contracts[0] =="pass":
            return None
        else:
            return contracts[0]
    else:
        return contracts[-4]

    
    
    
def valid_bidding(contracts, numbers):
    liste_contracts = contracts.copy()
    last = liste_contracts.pop()
    valid_numbers = []
    while last == "pass":
        if len(liste_contracts)==0:
            return numbers
        else:
            last = liste_contracts.pop()
    for number in numbers:
        if number > last.points:
            valid_numbers.append(number)
    return valid_numbers


