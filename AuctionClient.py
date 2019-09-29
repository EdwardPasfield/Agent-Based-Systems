import socket
import random
import operator
import math
from collections import Counter



class AuctionClient(object):
    """A client for bidding with the AucionRoom"""
    def __init__(self, host="localhost", port=8020, mybidderid=None, verbose=False):
        self.verbose = verbose
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host,port))
        forbidden_chars = set(""" '".,;:{}[]()""")
        if mybidderid:
            if len(mybidderid) == 0 or any((c in forbidden_chars) for c in mybidderid):
                print("""mybidderid cannot contain spaces or any of the following: '".,;:{}[]()!""")
                raise ValueError
            self.mybidderid = mybidderid
        else:
            self.mybidderid = raw_input("Input team / player name : ").strip()  # this is the only thing that distinguishes the clients
            while len(self.mybidderid) == 0 or any((c in forbidden_chars) for c in self.mybidderid):
              self.mybidderid = raw_input("""You input an empty string or included a space  or one of these '".,;:{}[]() in your name which is not allowed (_ or / are all allowed)\n for example Emil_And_Nischal is okay\nInput team / player name: """).strip()
        self.sock.send(self.mybidderid.encode("utf-8"))

        data = self.sock.recv(5024).decode('utf_8')
        x = data.split(" ")
        if self.verbose:
            print("Have received response of %s" % ' '.join(x))
        if(x[0] != "Not" and len(data) != 0):
          self.numberbidders = int(x[0])
          if self.verbose:
              print("Number of bidders: %d" % self.numberbidders)
          self.numtypes = int(x[1])
          if self.verbose:
              print("Number of types: %d" % self.numtypes)
          self.numitems = int(x[2])
          if self.verbose:
              print("Items in auction: %d" % self.numitems)
          self.maxbudget = int(x[3])
          if self.verbose:
              print("Budget: %d" % self.maxbudget)
          self.neededtowin = int(x[4])
          if self.verbose:
              print("Needed to win: %d" % self.neededtowin)
          self.order_known = "True" == x[5]
          if self.verbose:
              print("Order known: %s" % self.order_known)
          self.auctionlist = []
          self.winnerpays = int(x[6])
          if self.verbose:
              print("Winner pays: %d" % self.winnerpays)
          self.values = {}
          self.artists = {}
          order_start = 7
          if self.neededtowin > 0:
              self.values = None
              for i in range(7, 7+(self.numtypes*2), 2):
                  self.artists[x[i]] = int(x[i+1])
                  order_start += 2
              if self.verbose:
                  print("Item types: %s" % str(self.artists))
          else:
              for i in range(7, 7+(self.numtypes*3), 3):
                  self.artists[x[i]] = int(x[i+1])
                  self.values[x[i]] = int(x[i+2])
                  order_start += 3
              if self.verbose:
                  print("Item types: %s" % str(self.artists))
                  print ("Values: %s" % str(self.values))

          if self.order_known:
              for i in range(order_start, order_start+self.numitems):
                  self.auctionlist.append(x[i])
              if self.verbose:
                  print("Auction order: %s" % str(self.auctionlist))

        self.sock.send('connected '.encode("utf-8"))

        data = self.sock.recv(5024).decode('utf_8')
        x = data.split(" ")
        if x[0] != 'players':
            print("Did not receive list of players!")
            raise IOError
        if len(x) != self.numberbidders + 2:
            print("Length of list of players received does not match numberbidders!")
            raise IOError
        if self.verbose:
         print("List of players: %s" % str(' '.join(x[1:])))

        self.players = []

        for player in range(1, self.numberbidders + 1):
          self.players.append(x[player])

        self.sock.send('ready '.encode("utf-8"))

        self.standings = {name: {artist : 0 for artist in self.artists} for name in self.players}
        for name in self.players:
          self.standings[name]["money"] = self.maxbudget

    def play_auction(self):
        winnerarray = []
        winneramount = []
        done = False
        while not done:
            data = self.sock.recv(5024).decode('utf_8')
            x = data.split(" ")
            if x[0] != "done":
                if x[0] == "selling":
                    currentitem = x[1]
                    if not self.order_known:
                        self.auctionlist.append(currentitem)
                    if self.verbose:
                        print("Item on sale is %s" % currentitem)
                    bid = self.determinebid(self.numberbidders, self.neededtowin, self.artists, self.values, len(winnerarray), self.auctionlist, winnerarray, winneramount, self.mybidderid, self.players, self.standings, self.winnerpays)
                    if self.verbose:
                        print("Bidding: %d" % bid)
                    self.sock.send(str(bid).encode("utf-8"))
                    data = self.sock.recv(5024).decode('utf_8')
                    x = data.split(" ")
                    if x[0] == "draw":
                        winnerarray.append(None)
                        winneramount.append(0)
                    if x[0] == "winner":
                        winnerarray.append(x[1])
                        winneramount.append(int(x[3]))
                        self.standings[x[1]][currentitem] += 1
                        self.standings[x[1]]["money"] -= int(x[3])
            else:
                done = True
                if self.verbose:
                    if self.mybidderid in x[1:-1]:
                        print("I won! Hooray!")
                    else:
                        print("Well, better luck next time...")
        self.sock.close()

    def determinebid(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        '''You have all the variables and lists you could need in the arguments of the function,
        these will always be updated and relevant, so all you have to do is use them.
        Write code to make your bot do a lot of smart stuff to beat all the other bots. Good luck,
        and may the games begin!'''

        '''
        numberbidders is an integer displaying the amount of people playing the auction game.

        wincondition is an integer. A postive integer means that whoever gets that amount of a single type
        of item wins, whilst 0 means each itemtype will have a value and the winner will be whoever accumulates the
        highest total value before all items are auctioned or everyone runs out of funds.

        artists will be a dict of the different item types as keys with the total number of that type on auction as elements.

        values will be a dict of the item types as keys and the type value if wincondition == 0. Else value == None.

        rd is the current round in 0 based indexing.

        itemsinauction is a list where at index "rd" the item in that round is being sold is displayed. Note that it will either be as long as the sum of all the number of the items (as in "artists") in which case the full auction order is pre-announced and known, or len(itemsinauction) == rd+1, in which case it only holds the past and current items, the next item to be auctioned is unknown.

        winnerarray is a list where at index "rd" the winner of the item sold in that round is displayed.

        winneramount is a list where at index "rd" the amount of money paid for the item sold in that round is displayed.

        example: I will now construct a sentence that would be correct if you substituted the outputs of the lists:
        In round 5 winnerarray[4] bought itemsinauction[4] for winneramount[4] pounds/dollars/money unit.

        mybidderid is your name: if you want to reference yourself use that.

        players is a list containing all the names of the current players.

        standings is a set of nested dictionaries (standings is a dictionary that for each person has another dictionary
        associated with them). standings[name][artist] will return how many paintings "artist" the player "name" currently has.
        standings[name]['money'] (remember quotes for string, important!) returns how much money the player "name" has left.

            standings[mybidderid] is the information about you.
            I.e., standings[mybidderid]['money'] is the budget you have left.

        winnerpays is an integer representing which bid the highest bidder pays. If 0, the highest bidder pays their own bid,
        but if 1, the highest bidder instead pays the second highest bid (and if 2 the third highest, ect....). Note though that if you win, you always pay at least 1 (even if the second-highest was 0).

        Don't change any of these values, or you might confuse your bot! Just use them to determine your bid.
        You can also access any of the object variables defined in the constructor (though again don't change these!), or declare your own to save state between determinebid calls if you so wish.

        determinebid should return your bid as an integer. Note that if it exceeds your current budget (standings[mybidderid]['money']), the auction server will simply set it to your current budget.

        Good luck!
        '''

        # Game 1: First to buy wincondition of any artist wins, highest bidder pays own bid, auction order known.
        if (wincondition > 0) and (winnerpays == 0) and self.order_known:
            return self.first_bidding_strategy(numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays)

        # Game 2: First to buy wincondition of any artist wins, highest bidder pays own bid, auction order not known.
        if (wincondition > 0) and (winnerpays == 0) and not self.order_known:
            return self.second_bidding_strategy(numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays)

        # Game 3: Highest total value wins, highest bidder pays own bid, auction order known.
        if (wincondition == 0) and (winnerpays == 0) and self.order_known:
            return self.third_bidding_strategy(numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays)

        # Game 4: Highest total value wins, highest bidder pays second highest bid, auction order known.
        if (wincondition == 0) and (winnerpays == 1) and self.order_known:
            return self.fourth_bidding_strategy(numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays)

        # Though you will only be assessed on these four cases, feel free to try your hand at others!
        # Otherwise, this just returns a random bid.
        return self.random_bid(standings[mybidderid]['money'])

    def random_bid(self, budget):
        """Returns a random bid between 1 and left over budget."""
        #print("hi")
        return int(budget*random.random()+1)

    def first_bidding_strategy(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        """Game 1: First to buy wincondition of any artist wins, highest bidder pays own bid, auction order known."""
        #Define Constants
        bids = 0
        itemdict = dict.fromkeys(artists, 0)
        indexdict = { 'Van_Gogh' : 0, 'Picasso' : 0, 'Rembrandt' : 0, 'Da_Vinci' : 0 }
        rankdict = {'Van_Gogh' : 0, 'Picasso' : 0, 'Rembrandt' : 0, 'Da_Vinci' : 0}
        i = 0
        total = 0
        owned = False
        #Keep track of how much art owned by self
        for artist in artists:
            total += standings[mybidderid][artist]
        #Loop through artists
        for artist in artists:
            c = 0
            #find the index for each item in itemsinauction
            for index, item in enumerate(itemsinauction):
                #keep count and when they == 5 save the values to their dictionary
                if item == artist:
                    if c < 6:
                        c += 1
                    if c == wincondition:
                        #DICTIONARY FOR FIRST ONE TO 5 FROM START
                        if artist == 'Van_Gogh':
                            indexdict['Van_Gogh'] = index
                        if artist == 'Picasso':
                            indexdict['Picasso'] = index
                        if artist == 'Rembrandt':
                            indexdict['Rembrandt'] = index
                        if artist == 'Da_Vinci':
                            indexdict['Da_Vinci'] = index
        #Loop through artists
        for artist in artists:
            count = 0
            #Update Total
            total += standings[mybidderid][artist]
            #find the index of the artists when they first occur 5 times from the current round
            for index, item in enumerate(itemsinauction[rd:]):
                if item == artist:
                    if count < 6:
                        count += 1
                    if count == wincondition - total:
                        #DICTIONARY FOR FIRST TO 5 FROM CURRENT
                        if artist == 'Van_Gogh':
                            rankdict['Van_Gogh'] = index
                        if artist == 'Picasso':
                            rankdict['Picasso'] = index
                        if artist == 'Rembrandt':
                            rankdict['Rembrandt'] = index
                        if artist == 'Da_Vinci':
                            rankdict['Da_Vinci'] = index


        #Needed to be able to select the artist properlmyself. ORDERS artists by occurrence.
        for i in itemsinauction:
            d = {i: itemsinauction.count(i)}
            itemdict.update(d)

        #RANKS the dictionary item dict by values
        ranks = sorted(itemdict.items(), key=operator.itemgetter(1))
        #stores the minimum
        minimum = min(itemdict, key=itemdict.get)

        #Store the index of the artists to hit 5 occurences from current round
        likelihood = sorted(rankdict.items(), key=operator.itemgetter(1))
        startr = sorted(indexdict.items(), key=operator.itemgetter(1))
        #store the next to reach 5
        next = min(rankdict, key=rankdict.get)

        #IF PLAYERS >= 25
        if numberbidders >= 25:
            for name in artists:
                #AND NO ART IS OWNED
                if total == 0:
                    #BID ON THE NEXT TO OCCUR 5 TIMES
                    if itemsinauction[rd] == next:
                        bids = 200
                    else:
                        bids = 0
                else:
                    #IF ARTIST IS OWNED KEEP BIDDING
                    if standings[mybidderid][name] > 0:
                        if itemsinauction[rd] == name:
                            bids = 200
                #FAILSAFES
                if standings[mybidderid][name] == 4:
                    bids = standings[mybidderid]['money']

                if rd == 199:
                    bids = standings[mybidderid]['money']

        #MEDIOCRE - <25/>7
        else:
                    #IF BIDDERS < 7
                if numberbidders <= 7:
                    #Has to go for the most common in the top 20 due to the lack of bidders
                    #print(startr)
                    for artist in artists:
                        for player in players:
                            #If favourite from the start point is owned
                            if standings[player][startr[0][0]] > 0:
                                owned = True

                                """ If player is bidding a low amount for items like i am, out bid them up to 151 """
                            if rd >= 0:
                                #Loop through rounds to find the last payed value for each item
                                for r in range(0, rd):
                                    if winneramount[r] >= 0 and winneramount[r] < 151:
                                        #Bid for the favourite from start position
                                        if itemsinauction[rd] == startr[0][0]:
                                            if owned == False and total == 0:
                                                bids = 200
                                            elif standings[mybidderid][startr[0][0]] > 0:
                                                bids = 200
                                        #IF we do not get the favourite bid low for all others and try and outbid opponents
                                        elif itemsinauction[r] == itemsinauction[rd] and standings[mybidderid][startr[0][0]] == 0:
                                            bids = winneramount[r] + random.randint(1,3)
                                        elif  standings[mybidderid][startr[0][0]] == 0:
                                            bids = 5
                            else:
                                if standings[mybidderid][artist] == 4:
                                    bids = standings[mybidderid]['money']
                                bids = 0
                                """ IF player is about to win outbid by 1 """
                    #IF ANOTHER AGENT IS ABOUT TO WIN OUTBID THEM
                    for p in players:
                        for a in artists:
                            if itemsinauction[rd] == a and standings[p][a] == 4:
                                bids = standings[p]['money']+1
                # < 25
                #BID 201 for the 3rd to occur 5 times then 200 3 times and finish with 199
                elif itemsinauction[rd] == startr[2][0]:
                    if total == 0:
                        bids = 201
                    elif standings[mybidderid][startr[2][0]] == 4:
                        bids = 199
                    else:
                        bids = 200
        return bids



    def second_bidding_strategy(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        """Game 2: First to buy wincondition of any artist wins, highest bidder pays own bid, auction order not known."""
        bids = 0

        #RANKS the dictionary item dict by values
        ranks = sorted(artists.items(), key=operator.itemgetter(1))
        total = 0
        owned = False
        #Update total art owned
        for artist in artists:
            total += standings[mybidderid][artist]

        #For more than 25 bidders, bid on the econd best artist 200 everytime
        if numberbidders >= 25:
            if itemsinauction[rd] == ranks[1][0]:
                bids = 200
            else:
                bids = 0

        else:
        # IF BIDDERS < 25
            if numberbidders < 25:

                    #IF BIDDERS < 7
                if numberbidders <= 7:
                    #Has to go for the most common in the top 20 due to the lack of bidders

                    #loop through all artists and players
                    for artist in artists:
                        for player in players:

                            #If someone owns the best piece of art set owned to true
                            if standings[player][ranks[3][0]] > 0:
                                owned = True

                                """ If player is bidding a low amount for items like i am, out bid them up to 34 """
                            if rd >= 0:
                                #for all rounds if you win the most common piece of art stick with it bidding 200 each time

                                for r in range(0, rd):
                                    if itemsinauction[rd] == ranks[3][0]:
                                        if owned == False and total == 0:
                                            bids = 200
                                        elif standings[mybidderid][ranks[3][0]] > 0:
                                            bids = 200
                                    #If someone else wins it then bid low on all other art still outbidding other agents to save money
                                    elif itemsinauction[r] == itemsinauction[rd] and standings[mybidderid][ranks[3][0]] == 0:
                                        bids = winneramount[r] + random.randint(1, 3)
                                    elif standings[mybidderid][ranks[3][0]] == 0:
                                        bids = 5

                            else:

                                if standings[mybidderid][artist] == 4:
                                    bids = standings[mybidderid]['money']
                                bids = 0
                                """ IF player is about to win outbid by 1 """

                    # If someone is about to win, out bid them
                    for p in players:
                        for a in artists:
                            if itemsinauction[rd] == a and standings[p][a] == 4:
                                bids = standings[p]['money']+1
                else:
                    # < 25
                    #Bid 201 on the second most common artist
                    if itemsinauction[rd] == ranks[2][0]:
                        if total == 0:
                            bids = 201
                        #bid 199 for the final one.
                        elif standings[mybidderid][ranks[2][0]] == 4:
                            bids = 199
                        #Bid 200 every round
                        else:
                            bids = 200



            if rd >= 198:
                bids = standings[mybidderid]['money']
        return bids



    def third_bidding_strategy(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        """Game 3: Highest total value wins, highest bidder pays own bid, auction order known."""
        #bids = 0
        #DICTIONARY with the last paid winneramount and corresponding artist
        #Create a dictionary holding the artists and the last price bid for each
        solddict = dict(zip(itemsinauction, winneramount))
        allout = False
        i = 0

        #Loop to figure out if all other agents are out of money
        for player in players:
            if player != mybidderid and standings[player]['money'] == 0:
                i += 1
                if i == (len(players)-1):
                    allout = True
        r = 0
        for item in itemsinauction[rd:]:
            r += 1

        #####################################
        #Create dictionary storing the occurrences left in the game for each artist
        itemdict = dict.fromkeys(artists, 0)
        for i in itemsinauction:
            d = {i: itemsinauction[rd:].count(i)}
            itemdict.update(d)
        ##################################################
        #Calculation to figure out the remaining total possible values of the paintings
        total = ((itemdict['Van_Gogh'] * 6) + (itemdict['Picasso'] * 4) + (itemdict['Da_Vinci'] * 12) + (itemdict['Rembrandt'] * 8))

        #IF all other players are out the bid 1 for everything
        if allout == True:
            bids = 1
        if len(solddict) < 4:
            bids = 1
        else:
            for artist in artists:
                #Define variables to be used in formula calculation
                mon = standings[mybidderid]['money']
                val = values[artist]
                num = itemdict[artist]

                #print(solddict)
                if itemsinauction[rd] == artist:
                    #Calculate the upper limit for possible bids for the rest of the game for each artist
                    calc = math.floor(((( (val * num) / total) * mon) / ( (val * num) / numberbidders)) * val)
                    #For the first 140 rounds
                    if rd <=140:
                        if solddict[artist] < calc:
                            #if i didnt win the last time the artist appeared
                            if winnerarray[rd-1] != mybidderid:
                                #outbid last bid + a random amount
                                bids = solddict[artist] + random.randint(1, 5)
                    #ELSE bids = the upper limit
                            else:
                                bids = solddict[artist]
                        else:
                            bids = calc
                    else:
                        bids = calc

        #################################################################################

        # Currently just returns a random bid
        return bids

    def fourth_bidding_strategy(self, numberbidders, wincondition, artists, values, rd, itemsinauction, winnerarray, winneramount, mybidderid, players, standings, winnerpays):
        """Game 4: Highest total value wins, highest bidder pays second highest bid, auction order known."""
        # bids = 0
        # DICTIONARY with the last paid winneramount and corresponding artist
        #create dictionary for artists and the last price paid for them
        solddict = dict(zip(itemsinauction, winneramount))
        allout = False
        i = 0
        # print(len(players))
        #IF noone has any money left then bid 1 on everything
        for player in players:
            if player != mybidderid and standings[player]['money'] == 0:
                i += 1
                if i == (len(players) - 1):
                    allout = True
        r = 0
        for item in itemsinauction[rd:]:
            r += 1

        #####################################
        #update dictionary for current round
        itemdict = dict.fromkeys(artists, 0)
        for i in itemsinauction:
            d = {i: itemsinauction[rd:].count(i)}
            itemdict.update(d)

        ##################################################
        """
        total = ((itemdict['Van_Gogh'] * 6) + (itemdict['Picasso'] * 4) + (itemdict['Da_Vinci'] * 12) + (itemdict['Rembrandt'] * 8))
        
        mon = standings[mybidderid]['money']
        
        val = values[artist]
        
        num = itemdict[artist]
        
        calc = math.floor(((((val * num) / total) * mon) / ((val * num) / numberbidders)) * val)
        """
        #Calculate total remaining value for all the art.
        total = ((itemdict['Van_Gogh'] * 6) + (itemdict['Picasso'] * 4) + (itemdict['Da_Vinci'] * 12) + (
                itemdict['Rembrandt'] * 8))
        #if all players out of money bid 1 for all
        if allout == True:
            bids = 1
        if len(solddict) < 4:
            bids = 1
        else:

            for artist in artists:
                #Define variables used in calculation
                mon = standings[mybidderid]['money']
                val = values[artist]
                num = itemdict[artist]

                if itemsinauction[rd] == artist:
                    #Calculate the upper limit to bid for each artist
                    calc = math.floor(((((val * num) / total) * mon) / ((val * num) / numberbidders)) * val)
                    #For the first 140 rounds
                    if rd <= 140:
                        if solddict[artist] < calc:

                            if winnerarray[rd - 1] != mybidderid:
                                #out bid the last bid by random (1-8)
                                bids = solddict[artist] + random.randint(1, 8)
                #ELSE BID UPPER LIMIT + lil extra to be a bit more agressive
                            else:
                                # bayesian equilibrium
                                bids = solddict[artist]
                        else:
                                # bayesian equilibrium
                            bids = calc + random.randint(3,12)
                    else:
                        # bayesian equilibrium
                        bids = calc + random.randint(3,12)
                #LAST two rounds bid rest of money to not waste
                elif rd >= 198:
                    bids = standings[mybidderid]['money']
       
        return bids