import libtcodpy as libtcod
import math
import shelve
import textwrap

###TODO:
####### Pause menu
######### For cheat codes/word entry:
###### Each time they press a key, add the character to a 10 or so character
###### long string. Make sure it stays that long for space efficiency.
###### Then just see if that string ever contains the word contiguously
###### If so, do stuff
######### For Blinking mouse cursor:
###### keep track of how many frames have passed but reset every 300 or so
###### frames. Something like frameCount = (frameCount + 1) % 300 should work
###### Then just check if it is frames X-Y, if so change the color of the
###### tiles under the curson. If it's not, search for changed tiles and set them
###### back to default colors.
###### Maybe giving tiles a blinking instance variable for while they are non-standard
###### If so, we could specify what they should be when standard and when blinking.
######### Instructions screen at main menu
######### Opacity choices for menus, msmbox should be full opacity, those are important
######### EXP bar in GUI
######### Diagonal movement with num pad?
######### More artsy, vary the floor coloring, maybe walls too. 
###### Have a random variable to make some colors more/less common
######### Display what is under players feet in a different color than the mouse messages.

##############
# DEBUG MODE #
##############
DEBUG = False

#size of the windows
SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50

#Size of the map
MAP_WIDTH = 80
MAP_HEIGHT = 43

#constants for the rooms in the maps
ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

#GUI constants
BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT
MAIN_MENU_WIDTH = 24

#Message bar constants
#Makes messages go to the right of the health bar
MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

#FOV constants
FOV_ALGO = 0 #default FOV algorithm to use
FOV_LIGHT_WALLS = True #light the walls up or not
TORCH_RADIUS = 10 #how far the player sees, should be a variable in the object

#Item constants
MAX_INVENTORY_SIZE = 26
INVENTORY_WIDTH = 50
HEAL_AMOUNT = 4

#Menu constants
MAX_OPTIONS = 26
CHARACTER_SCREEN_WIDTH = 30
PAUSE_SCREEN_WIDTH = 20

#Experience and leveling constants
LEVEL_UP_BASE = 100
LEVEL_UP_FACTOR = 150
HEALTH_ON_LVL_UP = 20
STR_ON_LVL_UP = 1
DEF_ON_LVL_UP = 1
LVL_SCREEN_WIDTH = 50

#Spell constants
LIGHTNING_DAMAGE = 20
LIGHTNING_RANGE = 5

CONFUSE_NUM_TURNS = 10
CONFUSE_RANGE = 5

FIREBALL_RADIUS = 3
FIREBALL_DAMAGE = 12

#color constants
color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)

FPS_LIMIT = 20 #max FPS
GAME_TITLE = "Jules Quest, by Julian Jocque" #Title of window

class Rect:
    #A rectangle on the map
    def __init__(self, x, y, width, height):
        """Defines a rectangle on the map using the top-left x,y and the width and height of the desired rectangle"""
        self.x1 = x
        self.y1 = y
        self.x2 = x + width
        self.y2 = y + height
    
    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)
    
    def intersects(self, other):
        """Returns whether or not this rectangle intersects another"""
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)
    

class Tile:
    #One Tile of the Map
    def __init__(self, blocked, block_sight = None):
        self.blocked = blocked
        self.explored = False
        
        #If a tile is blocked, it blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight

class Object:
    #This is an object that appears on the screen
    def __init__(self, x, y, char, color, name, blocks = False, fighter = None, ai=None, item=None, alwaysVisible=False):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.blocks = blocks
        self.name = name
        self.alwaysVisible = alwaysVisible
        
        self.fighter = fighter
        if self.fighter != None: #lets the fighter component know who owns it
            self.fighter.owner = self

        self.ai = ai
        if self.ai != None: #lets the AI know how owns it
            self.ai.owner = self

        self.item = item
        if self.item != None: #Lets item know who owns it
            self.item.owner = self
    
    #Moves the character the given x and y
    def move(self, dx, dy):
        if not isBlocked(self.x + dx, self.y + dy): #Breaks when map[self.x] is undefined
            self.x += dx
            self.y += dy

    #Moves towards a target x,y one unit distance
    def moveTowards(self, targetX, targetY):
        #vector to target
        dx = targetX - self.x
        dy = targetY - self.y
        distance = math.sqrt(dx**2 + dy**2)

        #normalize vector to length of 1
        dx = int(round(dx/distance))
        dy = int(round(dy/distance))
        self.move(dx, dy)

    #Moves one object towards another target object, one unit distance at a time
    #Maybe make these two in to one thing, with optional parameters
    def moveTowards(self, other):
        #vector to target
        dx = other.x - self.x
        dy = other.y - self.y
        distance = self.distanceTo(other)

        #normalize vector to unit distance of one
        dx = int(round(dx/distance))
        dy = int(round(dy/distance))
        self.move(dx, dy)

    #Gives the distance from self to another object
    def distanceTo(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx**2 + dy**2)

    #Gives distance from self to co-ords
    def distance(self, x, y):
        return math.sqrt((x - self.x) ** 2 + (y - self.y) ** 2)

    #Moves or attacks, depeding on what is on the square we are targeting
    def moveOrAttack(self, dx, dy):
        global fovRecompute

        #Co-ords we are targeting
        x = self.x + dx
        y = self.y + dy

        #looks for something to attack
        target = None
        for object in objects:
            if object.fighter and object.x == x and object.y == y:
                target = object
                break

        #if we find a target, attack!
        if target is not None:
            player.fighter.attack(target)
        else:
            self.move(dx, dy)
            fovRecompute = True
    
    #Draws the object on to the screen
    def draw(self):
        if libtcod.map_is_in_fov(fovMap, self.x, self.y) or (self.alwaysVisible and map[self.x][self.y].explored):
            libtcod.console_set_foreground_color(con, self.color)
            libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)
        
    #Clears all chars on the x and y of this item
    def clear(self):
    #TODO: Have a "below" list for stacking items on screen
    #So that more than one item can be on one x, y co-ord
        libtcod.console_put_char(con, self.x, self.y, " ", libtcod.BKGND_NONE)
        
    #Puts this object on the bottom of the stack, so it is drawn last
    def sendToBottom(self):
        global objects
        objects.remove(self)
        objects.insert(0, self)

class Fighter:
    #combat-related properties and methods
    def __init__(self, hp, defense, power, xp, deathFunction=None):
        self.xp = xp
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power

        self.deathFunction = deathFunction

    #has this fighter take the specified amount of damage
    def takeDamage(self, damage):
        #apply damage if possible
        if damage > 0:
            self.hp -= damage
            #message("Now at " + str(self.hp) + " HP", libtcod.orange)

        #deals with the morbid business of death
        if self.hp <= 0:
            function = self.deathFunction
            if function != None:
                function(self.owner)
                if self.owner != player: #Something died that wasn't the player, so give experience
                    player.fighter.xp += self.xp

    #has the fighter attack the given target
    def attack(self, target):
        if target.fighter == None:
            message("You can't fight a harmless bystander!", libtcod.orange)

        #simply calculate how much damage this will do
        damage = self.power - target.fighter.defense

        if damage > 0:
            #Makes the target take damage
            message(self.owner.name.capitalize() + " attacks " + target.name + " for " + str(damage) + " hit points!", libtcod.orange)
            target.fighter.takeDamage(damage)
        else:
            #didn't do any damage
            message(self.owner.name.capitalize() + " attacks the " + target.name + " but it has no effect!" , libtcod.orange)

    def heal(self, amount):
        #heals the player for the given amount
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp

class BasicMonster:
    #AI for a basic monster:
    def takeATurn(self):
        #a basic monster takes its turn, it has same FOV as player
        monster = self.owner
        if libtcod.map_is_in_fov(fovMap, monster.x, monster.y):

            #chases player if they are far
            if monster.distanceTo(player) >= 2:
                monster.moveTowards(player)
            #now close enough to attack
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)

class ConfusedMonster():
    #AI for a confused monster
    def __init__(self, oldAI, numTurns = CONFUSE_NUM_TURNS):
        self.oldAI = oldAI
        self.numTurns = numTurns

    def takeATurn(self):
        #move in a random direction
        if self.numTurns <= 0:
            #Restore previous AI, no longer confused
            self.owner.ai = self.oldAI
            message("The " + self.owner.name + " is no longer confused!")
        else:
            #still confused, move in a random direction
            self.owner.move(libtcod.random_get_int(0, -1, 1), libtcod.random_get_int(0, -1, 1))
            self.numTurns -= 1

class Item:
    #an item that can be put in the inventory and used
    #TODO: Add weight to item and max weight adventurer can carry, based on LVL
    #Not based on STR due to oblivion syndrome of everyone needing STR
    def __init__(self, useFunction=None):
        self.useFunction = useFunction

    def use(self):
        #calls the use function if it is defined
        if self.useFunction == None:
            message("The " + self.owner.name + " cannot be used.")
        else:
            if self.useFunction() != "cancelled":
                inventory.remove(self.owner) #destroy after use, unless it was cancelled

    def pickUp(self):
        #add to player inventory, removes from map
        if len(inventory) >= MAX_INVENTORY_SIZE:
            #inventory is full
            message("Your inventory is full, cannot pick up " + 
                self.owner.name + ".", libtcod.red)
        else:
            #there is room in the inventory
            inventory.append(self.owner)
            objects.remove(self.owner)
            message("You picked up a " + str(self.owner.name) + "!", libtcod.green)

    def drop(self):
        #add to the map on the player's x, y and removes from inventory
        objects.append(self.owner)
        inventory.remove(self.owner)
        self.owner.x = player.x
        self.owner.y = player.y
        message("You dropped a " + self.owner.name + ".", libtcod.yellow)


######################
# Map Making Methods #
######################
def create_room(room):
    """Makes a room on the map given a rectangle"""
    global map
    for x in range(room.x1+1, room.x2):
        for y in range(room.y1+1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False


def create_h_tunnel(x1, x2, y): #TODO: Add a height parameter, add exception catching for out of range
    global map
    for x in range (min(x1,x2), max(x1,x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False
        
def create_v_tunnel(y1, y2, x): #TODO: These should be one function, in a "single map-piece" class
    global map
    for y in range (min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False


def makeMap():
    global map, player, objects, stairs

    #list of objects, with just the player to start
    objects = [player]
    
    #fills the map with blocked tiles
    map = [[ Tile(True)
        for y in range(MAP_HEIGHT) ]
            for x in range(MAP_WIDTH) ]
    
    rooms = []
    num_rooms = 0
    
    for r in range(MAX_ROOMS):
        width = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        height = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #gets a random position within boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - width - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - height - 1)
        
        new_room = Rect(x, y, width, height)
        failed = False
        for other_room in rooms:
            if new_room.intersects(other_room):
                failed = True
                break

        if not failed:
            #No intersection, so we carve the room
            #Paints the room to the map
            create_room(new_room)
            #Get the center of this room
            (new_x, new_y) = new_room.center()
            
            if num_rooms == 0:
                #If it's the first room we put the player in it
                player.x = new_x
                player.y = new_y
            else: #TODO: randomize instead of just always from center to center
                #not the first room, so we'll connect it to the previous room with a tunnel
                (prev_x, prev_y) = rooms[num_rooms - 1].center()
                
                #flips a coin to decide if we move horizontally or vertically first
                if libtcod.random_get_int(0, 0, 1) == 1:
                    #Horizontal first, then vertical
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    #Vertical first, then horizontal
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)
            
            #put some monsters in the new room
            placeObjects(new_room)
                
            #now we append to the list of rooms
            rooms.append(new_room)
            num_rooms += 1

    #puts stairs at the middle of the last room generated
    stairs = Object(new_x, new_y, ">", libtcod.white, "stairs", alwaysVisible=True)
    objects.append(stairs)


def advanceLevel():
    global dungeonLevel, player
    #Moves player to the next level
    message("You rest on the stairs for a bit, healing you.", libtcod.light_blue)
    player.fighter.heal(player.fighter.max_hp / 2)

    msgBox("You descend ever deeper in to the dungeon.\n", 30)
    makeMap()
    initializeFOV()
    dungeonLevel += 1


def renderAll():
    global fovMap, color_dark_wall, color_light_wall
    global color_dark_ground, color_light_ground
    global fovRecompute
    
    if fovRecompute:
        #message("Recomputing the FOV", libtcod.orange)
        fovRecompute = False
        libtcod.map_compute_fov(fovMap, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
    
    
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                visible = libtcod.map_is_in_fov(fovMap, x, y)
                wall = map[x][y].block_sight
                visited = map[x][y].explored
                if not visible:
                    if visited:
                        #if a tile is not visible but it was visited, we still display it
                        if wall:
                            #message("Not visible and a wall", libtcod.orange)
                            libtcod.console_set_back(con, x, y, color_dark_wall, libtcod.BKGND_SET)
                        else:
                            libtcod.console_set_back(con, x, y, color_dark_ground, libtcod.BKGND_SET)
                else:
                    #Once we see a tile it is considered explored
                    map[x][y].explored = True
                    
                    #currently visible to the player
                    if wall:
                        #message("Visible and a wall", libtcod.orange)
                        libtcod.console_set_back(con, x, y, color_light_wall, libtcod.BKGND_SET)
                    else:
                        #message("Visible and ground", libtcod.orange)
                        libtcod.console_set_back(con, x, y, color_light_ground, libtcod.BKGND_SET)

    #draw all objects in the list
    for object in objects:
        if object != player:
            object.draw()
    #draw player last so it is always on top
    player.draw()
 
    #blit the contents of "con" to the root console
    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

    #prepares the GUI panel
    libtcod.console_set_background_color(panel, libtcod.black)
    libtcod.console_clear(panel)

    #shows the players stats
    renderBar(1, 1, BAR_WIDTH, "HP", player.fighter.hp, player.fighter.max_hp,
        libtcod.light_red, libtcod.darker_red)

    #message(the game messages, one line at a time, libtcod.orange)
    y=1
    for(line, color) in gameMessages:
        libtcod.console_set_foreground_color(panel, color)
        libtcod.console_print_left(panel, MSG_X, y, libtcod.BKGND_NONE, line)
        y += 1

    #display names under the mouse
    libtcod.console_set_foreground_color(panel, libtcod.light_gray)
    libtcod.console_print_left(panel, 1, 0, libtcod.BKGND_NONE, getNamesUnderMouse())

    #blit the panel to the root console
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

  
def handleKeypresses():
    #Takes care of all the normal keys a player can press to interact
    #with the game  
    global gameState
    global fovRecompute

    keyPressed = libtcod.console_check_for_keypress(libtcod.KEY_PRESSED)
    keyChar = chr(keyPressed.c).lower()
    
    
    if (keyPressed.vk == libtcod.KEY_ENTER and (keyPressed.lalt or keyPressed.ralt)):
        #toggle fullscreen on alt+enter
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
    elif keyPressed.vk == libtcod.KEY_ESCAPE:
        #Exit on pressing escape
        return "exit"

    #Cotrols when the game is paused
    if gameState == "paused":
        if keyChar == "p":
            message("Game playing", libtcod.orange)
            gameState = "playing"
            keyChar = 0 #Clears out the buffer for keyPressed, if we don"t do that we get caught in an infinite pause/unpause loop
        else:
            return "did-not-move"

    #controls for normal gameplay
    if gameState == "playing":
        #movement keys
        if keyPressed.vk == libtcod.KEY_UP:
            player.moveOrAttack(0,-1)
            fovRecompute = True
        elif keyPressed.vk == libtcod.KEY_DOWN:
            player.moveOrAttack(0,1)
            fovRecompute = True
        elif keyPressed.vk == libtcod.KEY_LEFT:
            player.moveOrAttack(-1,0)
            fovRecompute = True
        elif keyPressed.vk == libtcod.KEY_RIGHT:
            player.moveOrAttack(1,0)
            fovRecompute = True
        elif keyChar == "p":
            message("Game paused", libtcod.orange)
            gameState = "paused"
            keyChar= 0 #Clears out the buffer for keyPressed, if we don"t do that we get caught in an infinite pause/unpause loop
            #TODO: Displayed paused game menu
        elif keyChar == "g":
            #pickup an item
            #TODO: let player choose what to pick up out of the stack
            for object in objects:
                if object.x == player.x and object.y == player.y and object.item:
                    object.item.pickUp()
                    break #breaks so we only pick up one item at a time
            return "did-not-move"
        elif keyChar == "i":
            #open the inventory
            chosenItem = inventoryMenu("Press the key next to an item to use it, any other key to cancel.\n")
            if chosenItem != None:
                chosenItem.use()
            return "did-not-move"
        elif keyChar == "d":
            #open inventory to drop an item
            chosenItem = inventoryMenu("Press the key next to an item to drop it, or any other key to cancel.\n")
            if chosenItem != None:
                chosenItem.drop()
        elif keyChar == "c":
            #show character info screen
            levelUpXP = LEVEL_UP_BASE + (player.level * LEVEL_UP_FACTOR) #TODO: Make this a helper function
            msgBox("Character Information:\n\nLevel: " + str(player.level) + "\nExperience: " + str(player.fighter.xp) + "/" + str(levelUpXP)\
                + "\nMax HP: " + str(player.fighter.max_hp) + "\nAttack: " + str(player.fighter.power) + "\nDefense: " +\
                 str(player.fighter.defense) + "\nMonsters Slain: " + str(player.monstersSlain) + "\n", CHARACTER_SCREEN_WIDTH)
        elif keyChar == ">" and player.x == stairs.x and player.y == stairs.y:
            advanceLevel()
        else:
            return "did-not-move"

    #controls for when the player is dead
    if gameState == "dead":
        if keyPressed.c == ord('r') or keyPressed.c == ord("R"):
            message("You've been revived!", libtcod.orange)
            player.fighter.hp = player.fighter.max_hp
            player.char = "@"
            player.color = libtcod.white
            gameState = "playing"



def placeObjects(room):
    num_monsters = fromDungeonLevel([[2,1], [3,4], [5,6]])
    monsterChances = {}
    monsterChances["orc"] = 80 #Always give an 80 chance to orcs
    monsterChances["troll"] = fromDungeonLevel([[15, 3], [30, 5], [60, 7], [200, 15]])
    monsterChances["goblin"] = fromDungeonLevel([[30, 1], [50, 6]])
    monsterChances["dragon"] = fromDungeonLevel([[1, 1], [10, 5], [80, 10]])
    
    for monster in range(num_monsters):
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1) #1s here to avoid
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1) #monsters spawning in walls
        monster = randomChoice(monsterChances)
        if monster == "orc":
            #make an orc
            fighterComponent = Fighter(hp=10, defense=0, power=3, xp=35, deathFunction=monsterDeath)
            aiComponent = BasicMonster()
            monster = Object(x, y, "o", libtcod.desaturated_green, "Orc" , blocks=True, fighter=fighterComponent, ai=aiComponent)
        elif monster == "troll":
            #make a troll
            fighterComponent = Fighter(hp=16, defense=1, power=4, xp=130, deathFunction=monsterDeath)
            aiComponent = BasicMonster()
            monster = Object(x, y, "T", libtcod.darker_green, "Troll", blocks=True, fighter=fighterComponent, ai=aiComponent)
        elif monster == "goblin":
            #make a goblin
            fighterComponent = Fighter(hp=20, defense = 0, power = 2, xp=40, deathFunction=monsterDeath)
            aiComponent = BasicMonster()
            monster = Object(x, y, "g", libtcod.green, "Goblin", blocks=True, fighter=fighterComponent, ai=aiComponent)
        elif monster == "dragon":
            #make a dragon, would like more interesting AI
            fighterComponent = Fighter(hp=100, defense=10, power=20, xp=1000, deathFunction=monsterDeath)
            aiComponent= BasicMonster()
            monster = Object(x, y, "D", libtcod.red, "Dragon", blocks=True, fighter=fighterComponent, ai=aiComponent)
           
        objects.append(monster)

    #pick a random number of objects for this room based on dungeon level
    currentMaxItems = fromDungeonLevel([[1,1], [2,4], [3, 6]])
    num_items = libtcod.random_get_int(0, 0, currentMaxItems)
    for i in range(num_items):
        #Pick a random spot to put the room, should make helper method
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1) #1s here to avoid
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1) #items spawning in walls

        #only place if tile not blocked
        if not isBlocked(x, y):
            if not DEBUG:
                itemChoices = {}
                itemChoices["heal"] = 60
                itemChoices["confuse"] = fromDungeonLevel([[25,2]])
                itemChoices["lightning"] = fromDungeonLevel([[40, 5]])
                itemChoices["fireball"] = fromDungeonLevel([[20, 6]])
                choice =  randomChoice(itemChoices)
                if choice == "heal":
                    #60% chance to make a healing potion
                    item_component = Item(useFunction=castHeal)
                    item = Object(x, y, "!", libtcod.violet,"Healing Potion", item=item_component, alwaysVisible=True)
                elif choice == "confuse":
                    #13% chance of a confuse scroll
                    item_component = Item(useFunction=castConfuse)
                    item = Object(x, y, "#", libtcod.darker_violet, "Scroll of Confusion", item=item_component, alwaysVisible=True)
                elif choice == "lightning":
                    #14% chance to make a lighting bolt scroll
                    item_component = Item(useFunction=castLightning)
                    item = Object(x, y, "#", libtcod.yellow, "Scroll of Lightning", item=item_component, alwaysVisible=True)
                elif choice == "fireball":
                    #13$ chance to make a fireball scroll
                    item_component = Item(useFunction=castFireball)
                    item = Object(x, y, "#", libtcod.red, "Scroll of Fireball", item=item_component, alwaysVisible=True)
                objects.append(item)
                item.sendToBottom() #always want items on bottom of stack
            else:
                #DEBUG MODE, SPAWNS ONLY 1 TYPE OF ITEM, AND MANY
                function = castConfuse
                item_component = Item(useFunction=function)
                item1 = Object(x, y, "D", libtcod.red, str(function), item=item_component)
                objects.append(item1)
                item2 = Object(x+1, y, "D", libtcod.red, str(function), item=item_component)
                objects.append(item2)
                item3 = Object(x, y+1, "D", libtcod.red, str(function), item=item_component)
                objects.append(item3)
                item4 = Object(x+1, y+1, "D", libtcod.red, str(function), item=item_component)
                objects.append(item4)

def isBlocked(x, y):
    #Checks if a given x, y has something on it
    #test for map tile
    if map[x][y].blocked:
        return True
     
    #check objects
    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True
    
    return False

def checkLevelUp():
    global player
    #Checks if the player should be given a level up
    levelUpXP = LEVEL_UP_BASE + (player.level * LEVEL_UP_FACTOR)
    if player.fighter.xp >= levelUpXP:
        #level up the player
        player.level += 1
        player.fighter.xp -= levelUpXP
        message("You grow stronger! You've leveled up to " + str(player.level) + "!", libtcod.yellow)

        #asks the player what they want to level up
        choice = None
        while choice == None:
            levelUpChoices = \
            ["Constitution (+" + str(HEALTH_ON_LVL_UP) + " HP going from " + str(player.fighter.max_hp) + " to " + str(player.fighter.max_hp + HEALTH_ON_LVL_UP) + ")",
            "Strength (+" + str(STR_ON_LVL_UP) + " attack going from " + str(player.fighter.power) + " to " + str(player.fighter.power + STR_ON_LVL_UP) + ")",
            "Defense (+" + str(DEF_ON_LVL_UP) + " defense going from " + str(player.fighter.defense) + " to " + str(player.fighter.defense + DEF_ON_LVL_UP) + ")"]
            choice = menu("You leveled up! Pick a stat to raise:\n", levelUpChoices, LVL_SCREEN_WIDTH)
            if choice == 0:
                player.fighter.max_hp += HEALTH_ON_LVL_UP
                player.fighter.hp += HEALTH_ON_LVL_UP
            elif choice == 1:
                player.fighter.power += STR_ON_LVL_UP
            elif choice == 2:
                player.fighter.defense += DEF_ON_LVL_UP

def fromDungeonLevel(table):
    #Returns a value that depends on the level. Table specifies what value occurs after each level, deaults to 0.
    for (value, level) in reversed(table):
        if dungeonLevel >= level:
            return value
    return 0


#################
# Death methods #
#################
def playerDeath(player):
    #player died, game over!
    global gameState
    player.fighter.hp = 0 #avoids getting negative HP when dead
    message("You died! Press R to respawn!", libtcod.red)
    gameState = "dead"

    #make the player in to a corpse
    player.char = "%"
    player.color = libtcod.dark_red

def monsterDeath(monster):
    global player

    #Transform monster in to a corpse, can't move or attack/be attacked
    message(monster.name.capitalize() + " is dead! You gained " + str(monster.fighter.xp) + " XP!", libtcod.red)
    monster.char = "%"
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = "Remains of " + monster.name
    monster.sendToBottom()
    player.monstersSlain += 1

##############
# UI Methods #
##############
def renderBar(x, y, total_width, name, value, maximum, barColor, backColor):
    #Renders a status bar, first we calculate the width of it
    bar_width = int(float(value) / maximum * total_width)

    #render the background
    libtcod.console_set_background_color(panel, backColor)
    libtcod.console_rect(panel, x, y, total_width, 1, False)

    #Now render the top of the bar
    libtcod.console_set_background_color(panel, barColor)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False)

    #text to denote what the bar is of
    libtcod.console_set_foreground_color(panel, libtcod.white)
    libtcod.console_print_center(panel, x + total_width/2, y, libtcod.BKGND_NONE,
        name + ": " + str(value) + "/" + str(maximum))

def message(new_msg, color = libtcod.white):
    #wrap text around if it's too long
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
        #if the buffer is full, delete the oldest msg to make room
        if len(gameMessages) == MSG_HEIGHT:
            del gameMessages[0]

        #add the new line as a tuple, with text and color
        gameMessages.append((line, color))

def getNamesUnderMouse():
    #returns a tring with the name of all objects under the mouse
    mouse = libtcod.mouse_get_status()
    (x, y) = (mouse.cx, mouse.cy)

    #make a list with name of all objects under mouse and in FOV
    names =[]
    for object in objects:
        if object.x == x and object.y == y and libtcod.map_is_in_fov(fovMap,
            object.x, object.y):
            names.append(object.name)

    #Join all the names in to one string
    names = ", ".join(names)
    return names.capitalize()


################
# Menu Methods #
################
def menu(header, options, width):
    if len(options) > MAX_OPTIONS:
        raise ValueError("Cannot have a meny with more than " + str(MAX_OPTIONS) + "options.")

    #calculate the height for the menu, inclues 1 tile per line of header (after wrap)
    #and 1 line per option
    if header == "":
        headerHeight = 0
    else:
        headerHeight = libtcod.console_height_left_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    height = len(options) + headerHeight

    #make an off-screen console that is the menu window
    window = libtcod.console_new(width, height)

    #print header, with word wrap
    libtcod.console_set_foreground_color(window, libtcod.white)
    libtcod.console_print_left_rect(window, 0, 0, width, height, libtcod.BKGND_NONE, header)

    #prints the options to the menu
    y = headerHeight
    letterIndex = ord("a")
    for optionText in options:
        text = "(" + chr(letterIndex) + ")" + optionText
        libtcod.console_print_left(window, 0, y, libtcod.BKGND_NONE, text)
        y += 1
        letterIndex += 1

    #blit the contents of the window to the root console
    x = SCREEN_WIDTH/2 - width/2
    y = SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

    #present the root console to player and wait for a keypress
    libtcod.console_flush()
    keyPressed = libtcod.console_wait_for_keypress(True)

    #Allows for full-screening with Alt+Enter in menus
    if keyPressed.vk == libtcod.KEY_ENTER and (keyPressed.lalt or keyPressed.ralt):
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen)

    #after they press a key, see which it was an do the appropriate thing
    index = keyPressed.c - ord("a")
    if index >= 0 and index < len(options):
        return index
    return None

def mainMenu():
    image = libtcod.image_load("menu_background1.png")

    while not libtcod.console_is_window_closed():
        #Shows the background image
        libtcod.image_blit_2x(image, 0, 0, 0)

        #shows the game title and author
        libtcod.console_set_foreground_color(0, libtcod.light_orange)
        libtcod.console_print_center(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-5, libtcod.BKGND_NONE, "Jules Quest")
        libtcod.console_print_center(0, SCREEN_WIDTH/2, SCREEN_HEIGHT/2-3, libtcod.BKGND_NONE, "By Julian Jocque")

        menuOptions = ["New Game", "Continue", "Quit"]
        #shows options and waits for a choice

        choice = menu("", menuOptions, MAIN_MENU_WIDTH)

        if choice == 0: #new game
            newGame()
            playGame()
        elif choice == 1: #continue
            try:
                loadGame()
                playGame()
            except:
                msgBox("\n No save file found.\n", MAIN_MENU_WIDTH)
                continue
        #elif choice == 2: #show instructions
        #    menu("\nArrow Keys to move and attack monsters.\nG to pickup an item you are standing on.\nI to open Inventory.\n" +\
        #        "D to open Drop menu.\nP to pause and unpause.\nC to open Character information screen.\n> to go down stairs.\n" +\
        #        "Mouse over a tile to see what is on it, either monsters or items.\n", [], SCREEN_WIDTH/2)
        elif choice == 2: #quit
            break
        

def inventoryMenu(header):
    #Show menu with one option per item in the inventory
    if len(inventory) == 0:
        options=["Inventory is empty."]
    else:
        options = [item.name for item in inventory]

    index = menu(header, options, INVENTORY_WIDTH)

    #if an item was chosen, return it
    if index == None or len(inventory) == 0:
        return None
    return inventory[index].item

def msgBox(text, width=SCREEN_WIDTH-30):
    #Uses menu() as a message box
    menu(text + "\nPress any key to continue.", [], width)

def saveGame():
    #makes a new shelve to write game data, overwrites any old data
    global map, objects, inventory, gameState, gameMessages, player, stairs, dungeonLevel

    file = shelve.open("savegame", "n")
    file["map"] = map
    file["objects"] = objects
    file["inventory"] = inventory
    file["gameState"] = gameState
    file["gameMessages"] = gameMessages
    file["playerIndex"] = objects.index(player)
    file["stairsIndex"] = objects.index(stairs)
    file["dungeonLevel"] = dungeonLevel
    file.close()

def loadGame():
    #opens the old shelf and puts all the stuff in there in to our variables
    global map, objects, inventory, gameState, gameMessages, player, stairs, dungeonLevel

    file = shelve.open("savegame", "r")
    map = file["map"]
    objects = file["objects"]
    inventory = file["inventory"]
    player = objects[file["playerIndex"]]
    gameMessages = file["gameMessages"]
    gameState = file["gameState"]
    stairs = objects[file["stairsIndex"]]
    dungeonLevel = file["dungeonLevel"]
    file.close()

    #might want to save the FOV map as well, for now it will just black it out for the player upon loading
    initializeFOV()


##################
# Item abilities #
##################
def castHeal():
    #heals the player
    if player.fighter.hp == player.fighter.max_hp:
        message("You are already at full health.")
        return "cancelled"
    
    message("You healed for " + str(HEAL_AMOUNT) + "!")
    player.fighter.heal(HEAL_AMOUNT)

def castLightning():
    #finds the closest monster and damages it
    monster = closestMonster(LIGHTNING_RANGE)
    if monster == None:
        message("No monster close enough to hit.", libtcod.red)
        return "cancelled"

    message("A Lightning Bolt strikes the " + monster.name + " thunderously for " + 
        str(LIGHTNING_DAMAGE) + " HP.", libtcod.light_blue)
    monster.fighter.takeDamage(LIGHTNING_DAMAGE)

def castConfuse():
    #confuses a target the player gives us
    message("Please choose a monster to confuse.", libtcod.violet)
    monster = targetMonster(CONFUSE_RANGE)
    if monster == None:
        return "cancelled"
    else:
        oldAI = monster.ai
        monster.ai = ConfusedMonster(oldAI)
        monster.ai.owner = monster #tells component who owns it
        message("The " + monster.name + " starts stumbling about aimlessly!")

def castConfusenClosest():
    #finds the closest monster and confuses them
    monster = closestMonster(CONFUSE_RANGE)
    if monster == None:
        message("There are no monsters close enough to confuse.", libtcod.red)
        return "cancelled"
    else:
        oldAI = monster.ai
        monster.ai = ConfusedMonster(oldAI)
        monster.ai.owner = monster #tells component who owns it
        message("The " + monster.name + " starts stumbling about aimlessly!")


def castFireball():
    #casts fireball at the target chosen by the player
    #TODO: MUST display where it hit, so people know what the radius is.
    message("Left-Click a target tile for the fireball, or right-click to cancel.", libtcod.light_blue)
    (x,y) = targetTile()
    if x == None:
        #They cancelled
        return "cancelled"
    else:
        #They cast!
        message("The fireball explodes! Burning everything within " + str(FIREBALL_RADIUS) + " tiles.")

        for object in objects:
            if object.distance(x,y) <= FIREBALL_RADIUS and object.fighter != None:
                message("The " + object.name + " gets burned for " + str(FIREBALL_DAMAGE) + 
                    " hit points!")
                object.fighter.takeDamage(FIREBALL_DAMAGE)


def closestMonster(maxRange):
    #finds the closest monster in FOV from the player and returns it
    closestDist = maxRange + 1
    closestMonster = None
    for object in objects:
        #print "Found a fighter: " + str(object.fighter != None)
        if object.fighter != None and object != player and libtcod.map_is_in_fov(fovMap, object.x, object.y):
            distance = player.distanceTo(object)
            #print "Distance to it is: " + str(distance)
            if distance < closestDist:
                closestDist = distance
                closestMonster = object
    return closestMonster

def targetTile(maxRange=None):
    #Returns the position of the tile in player's FOV
    #Should be expanded to blink the radius of the spell with a given color
    while True:
        renderAll()
        libtcod.console_flush()

        key = libtcod.console_check_for_keypress()
        mouse = libtcod.mouse_get_status()
        (x, y) = mouse.cx, mouse.cy

        if (mouse.lbutton_pressed and libtcod.map_is_in_fov(fovMap, x, y)) and (maxRange == None or player.distance(x, y) <= maxRange):
            return (x, y)
        if mouse.rbutton_pressed:
            #cancel if they right click, might want to add more ways to cancel
            message("Spell canceled.", libtcod.white)
            return (None, None)

def targetMonster(maxRange=None):
    #Returns a clicked monster that is within range of the spell, and in FOV.
    #Return None is spell cast was canceled
    while True:
        (x, y) = targetTile(maxRange)
        if x == None:
            #player canceled the spell cast
            message("Spell canceled.", libtcod.white)
            return None

        #return first clicked monster, otherwise keep looping
        for object in objects:
            if object.x == x and object.y == y and object != player and libtcod.map_is_in_fov(fovMap, x, y) and not object.item:
                return object

def randomChoiceIndex(chances):
    #Choose an option from a list of chances, returning the index
    dice = libtcod.random_get_int(0, 1, sum(chances))

    #go through all the chances, keeping the sum so far
    total = 0
    choice = 0
    for item in chances:
        total += item

        #check if dice landed on this choice
        if dice <= total:
            return choice
        choice += 1

def randomChoice(choices_dict):
    #Given a dictionary of choices with the name of the choice as the keys and the chances that choice should happen as
    #the values, this returns the key of the randomly chosen entry
    chances = choices_dict.values()
    strings = choices_dict.keys()

    return strings[randomChoiceIndex(chances)]

############################
# Initialization Functions #
############################
def newGame():
    global player, inventory, gameMessages, gameState, dungeonLevel

    #start at the start
    dungeonLevel = 1

    #makes the player object
    fighterComponent = Fighter(hp=30, defense=2, power=5, xp=0, deathFunction=playerDeath) #don't need the "hp=", "defense=", but this is easier to read.
    player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, "@", libtcod.white, "Jules", blocks=True, fighter=fighterComponent)
    player.level = 1
    player.monstersSlain = 0


    #generate a dungeon map
    makeMap()

    gameState = "playing"

    #Messages log, with their colors
    gameMessages = []

    #player inventory
    inventory = []

    #Welcome message for the new game
    message("Welcome to the universe.", libtcod.orange)

    #initialzes the player's FOV
    initializeFOV()

def initializeFOV():
    global fovRecompute, fovMap
    fovRecompute = True

    #unexplored areas start black
    libtcod.console_clear(con)

    fovMap = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    #makes the FOV map, based on the generated map
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fovMap, x, y, not map[x][y].block_sight, not map[x][y].blocked)

def playGame():
    playerAction = None

    while not libtcod.console_is_window_closed():
        #renders the screen
        renderAll()

        checkLevelUp()

        libtcod.console_flush()

        #erase all objects in their old positions, before they move
        for object in objects:
            object.clear()

        #handles keypresses, exits if needed
        playerAction = handleKeypresses()
        if playerAction == "exit":
            saveGame()
            break

        #monster turn
        if gameState == "playing" and playerAction != "did-not-move":
            for object in objects:
                if object.ai:
                    object.ai.takeATurn()


#########################
# System Initialization #
#########################
libtcod.console_set_custom_font("arial10x10.png", libtcod.FONT_TYPE_GRAYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, GAME_TITLE, False) #False here is for fullscreen
libtcod.sys_set_fps(FPS_LIMIT)

con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)
objects = []

##############
# Game Start #
##############
if DEBUG:
    newGame()
    playGame()
else:
    mainMenu()