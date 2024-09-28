"""
This file contains code for a board game on command-line interface with Ollama integrated into it.
Author: SoftwareApkDev
"""


# Game version: 1


# Importing necessary libraries


import sys
import time
import uuid
import pickle
import copy
from langchain_ollama import OllamaLLM
import random
import os
from functools import reduce
import subprocess

from mpmath import mp, mpf

mp.pretty = True


# Creating static variables to be used throughout the game.


LETTERS: str = "abcdefghijklmnopqrstuvwxyz"
MODELS: list = ["llama3.2", "llama3.2:1b", "llama3.1", "llama3.1:70b", "llama3.1:405b", "phi3", "phi3:medium",
                "gemma2:2b", "gemma2", "gemma2:27b", "mistral", "moondream", "neural-chat", "starling-lm", "codellama",
                "llama2-uncensored", "llava", "solar"]


# Creating static functions to be used throughout the game.


def is_number(string: str) -> bool:
    try:
        mpf(string)
        return True
    except ValueError:
        return False


def triangular(n: int) -> int:
    return int(n * (n - 1) / 2)


def mpf_sum_of_list(a_list: list) -> mpf:
    return mpf(str(sum(mpf(str(elem)) for elem in a_list if is_number(str(elem)))))


def mpf_product_of_list(a_list: list) -> mpf:
    return mpf(reduce(lambda x, y: mpf(x) * mpf(y) if is_number(x) and
                                                      is_number(y) else mpf(x) if is_number(x) and not is_number(
        y) else mpf(y) if is_number(y) and not is_number(x) else 1, a_list, 1))


def generate_random_name() -> str:
    res: str = ""  # initial value
    name_length: int = random.randint(3, 25)
    for i in range(name_length):
        res += LETTERS[random.randint(0, len(LETTERS) - 1)]

    return res.capitalize()


def load_game_data(file_name):
    # type: (str) -> SavedGameData
    return pickle.load(open(file_name, "rb"))


def save_game_data(game_data, file_name):
    # type: (SavedGameData, str) -> None
    pickle.dump(game_data, open(file_name, "wb"))


def clear():
    # type: () -> None
    if sys.platform.startswith('win'):
        os.system('cls')  # For Windows System
    else:
        os.system('clear')  # For Linux System


# Creating necessary classes for the game.


class Dice:
    """
    This class contains attributes of the dice in the game.
    """

    def __init__(self):
        # type: () -> None
        self.value: int = random.randint(1, 6)

    def __str__(self):
        # type: () -> str
        return "Value: " + str(self.value) + "\n"

    def clone(self):
        # type: () -> Dice
        return copy.deepcopy(self)


class Board:
    """
    This class contains attributes of the board in this game.
    """

    def __init__(self, tiles):
        # type: (list) -> None
        self.__tiles: list = tiles

    def __str__(self):
        # type: () -> str
        res: str = "Current board representation:\n\n"
        for tile in self.__tiles:
            res += str(tile) + "\n"

        return res

    def get_tiles(self):
        # type: () -> list
        return self.__tiles

    def clone(self):
        # type: () -> Board
        return copy.deepcopy(self)


class Tile:
    """
    This class contains attributes of a tile on the board.
    """

    TILE_NUMBER: int = 0

    def __init__(self, name, description):
        # type: (str, str) -> None
        Tile.TILE_NUMBER += 1
        self.name: str = name
        self.description: str = description

    def __str__(self):
        # type: () -> str
        res: str = ""  # initial value
        res += "Name: " + str(self.name) + "\n"
        res += "Description: " + str(self.description) + "\n"
        return res

    def clone(self):
        # type: () -> Tile
        return copy.deepcopy(self)


class StartTile(Tile):
    """
    This class contains attributes of the start tile where the player can gain awards by passing or landing on it.
    """

    def __init__(self):
        # type: () -> None
        Tile.__init__(self, "START TILE", "A tile where the player can gain awards by passing or landing on it.")


class EmptySpace(Tile):
    """
    This class contains attributes of an empty space where nothing happens if the player lands on it.
    """

    def __init__(self):
        # type: () -> None
        Tile.__init__(self, "EMPTY SPACE", "A tile where nothing happens if the player lands on it.")


class Place(Tile):
    """
    This class contains attributes of a place the player can purchase and upgrade when landing on it.
    """

    def __init__(self, name, description, gold_cost, gold_per_turn, exp_per_turn):
        # type: (str, str, mpf, mpf, mpf) -> None
        Tile.__init__(self, name, description)
        self.level: int = 1
        self.gold_cost: mpf = gold_cost
        self.gold_per_turn: mpf = gold_per_turn
        self.exp_per_turn: mpf = exp_per_turn
        self.owner: Player or None = None  # initial value

    def __str__(self):
        # type: () -> str
        res: str = Tile.__str__(self)  # initial value
        res += "Level: " + str(self.level) + "\n"
        res += "Gold Cost: " + str(self.gold_cost) + "\n"
        res += "Gold Per Turn: " + str(self.gold_per_turn) + "\n"
        res += "EXP Per Turn: " + str(self.exp_per_turn) + "\n"
        res += "Owner: "
        if self.owner is None:
            res += "None\n"
        else:
            res += str(self.owner.name) + "\n"
        return res

    def level_up(self):
        # type: () -> None
        self.level += 1
        self.gold_cost *= mpf("10") ** triangular(self.level)
        self.gold_per_turn *= mpf("10") ** (triangular(self.level) - 1)
        self.exp_per_turn *= mpf("10") ** (triangular(self.level) - 1)


class RandomRewardTile(Tile):
    """
    This class contains attributes of a tile where the player can gain random rewards.
    """

    def __init__(self):
        # type: () -> None
        Tile.__init__(self, "RANDOM REWARD TILE", "A tile granting random rewards to the player landing on it.")


class UpgradeShop(Tile):
    """
    This class contains attributes of an upgrade shop where the player can buy upgrades.
    """

    def __init__(self, upgrades_sold):
        # type: (list) -> None
        Tile.__init__(self, "UPGRADE SHOP", "A tile where the player can buy upgrades.")
        self.__upgrades_sold: list = upgrades_sold

    def get_upgrades_sold(self):
        # type: () -> list
        return self.__upgrades_sold

    def __str__(self):
        # type: () -> str
        res: str = str(self.name) + "\n"
        res += "Below is a list of upgrades sold:\n"
        for upgrade in self.__upgrades_sold:
            res += str(upgrade) + "\n"

        return res


class RandomReward:
    """
    This class contains attributes of an obtainable random reward at random reward tiles.
    """

    def __init__(self):
        # type: () -> None
        self.reward_gold: mpf = mpf("1e" + str(random.randint(1000, 100000)))
        self.reward_exp: mpf = mpf("1e" + str(random.randint(1000, 100000)))

    def __str__(self):
        # type: () -> str
        res: str = ""  # initial value
        res += "Reward Gold: " + str(self.reward_gold) + "\n"
        res += "Reward EXP: " + str(self.reward_exp) + "\n"
        return res

    def clone(self):
        # type: () -> RandomReward
        return copy.deepcopy(self)


class Upgrade:
    """
    This class contains attributes of an upgrade the player can purchase to improve the amount
    of gold and EXP earned per turn.
    """

    def __init__(self, name, description, gold_cost, gold_gain_multiplier, exp_gain_multiplier):
        # type: (str, str, mpf, mpf, mpf) -> None
        self.name: str = name
        self.description: str = description
        self.gold_cost: mpf = gold_cost
        self.gold_gain_multiplier: mpf = gold_gain_multiplier
        self.exp_gain_multiplier: mpf = exp_gain_multiplier

    def __str__(self):
        # type: () -> str
        res: str = ""  # initial value
        res += "Name: " + str(self.name) + "\n"
        res += "Description: " + str(self.description) + "\n"
        res += "Gold Cost: " + str(self.gold_cost) + "\n"
        res += "Gold Gain Multiplier: " + str(self.gold_gain_multiplier) + "\n"
        res += "EXP Gain Multiplier: " + str(self.exp_gain_multiplier) + "\n"
        return res

    def clone(self):
        # type: () -> Upgrade
        return copy.deepcopy(self)


class Player:
    """
    This class contains attributes of the player in this game.
    """

    def __init__(self, name):
        # type: (str) -> None
        self.player_id: str = str(uuid.uuid1())
        self.name: str = name
        self.level: int = 1
        self.location: int = 0  # initial value
        self.gold: mpf = mpf("1e6")
        self.exp: mpf = mpf("0")
        self.required_exp: mpf = mpf("1e6")
        self.__owned_list: list = []  # initial value
        self.__upgrade_list: list = []  # initial value

    def __str__(self):
        # type: () -> str
        res: str = ""  # initial value
        res += "Player ID: " + str(self.player_id) + "\n"
        res += "Name: " + str(self.name) + "\n"
        res += "Level: " + str(self.level) + "\n"
        res += "Location: " + str(self.location) + "\n"
        res += "Gold: " + str(self.gold) + "\n"
        res += "EXP: " + str(self.exp) + "\n"
        res += "Required EXP: " + str(self.required_exp) + "\n"
        res += "Below is a list of places owned by the player:\n"
        for place in self.__owned_list:
            res += str(place) + "\n"

        res += "Below is a list of upgrades owned by the player:\n"
        for upgrade in self.__upgrade_list:
            res += str(upgrade) + "\n"

        return res

    def level_up(self):
        # type: () -> None
        while self.exp >= self.required_exp:
            self.level += 1
            self.required_exp *= mpf("10") ** triangular(self.level)

    def roll_dice(self, game):
        # type: (SavedGameData) -> None
        self.location += Dice().value
        if self.location >= len(game.board.get_tiles()):
            self.gold += game.start_bonus
            self.location -= len(game.board.get_tiles())

    def get_gold_per_turn(self):
        # type: () -> mpf
        return mpf_sum_of_list([place.gold_per_turn for place in self.__owned_list]) * \
            mpf_product_of_list([upgrade.gold_gain_multiplier for upgrade in self.__upgrade_list])

    def get_exp_per_turn(self):
        # type: () -> mpf
        return mpf_sum_of_list([place.exp_per_turn for place in self.__owned_list]) * \
            mpf_product_of_list([upgrade.exp_gain_multiplier for upgrade in self.__upgrade_list])

    def get_owned_list(self):
        # type: () -> list
        return self.__owned_list

    def buy_place(self, place):
        # type: (Place) -> bool
        if self.gold >= place.gold_cost:
            self.gold -= place.gold_cost
            self.__owned_list.append(place)
            place.owner = self
            return True
        return False

    def upgrade_place(self, place):
        # type: (Place) -> bool
        if place in self.__owned_list:
            if self.gold >= place.gold_cost:
                self.gold -= place.gold_cost
                place.level_up()
                return True
            return False
        return False

    def acquire_place(self, place, owner):
        # type: (Place, Player) -> bool
        if place in owner.get_owned_list() and place not in self.get_owned_list():
            if self.gold >= place.gold_cost:
                self.gold -= place.gold_cost
                owner.gold += place.gold_cost
                place.level_up()
                self.__owned_list.append(place)
                owner.__owned_list.append(place)
                place.owner = self
                return True
            return False
        return False

    def get_upgrade_list(self):
        # type: () -> list
        return self.__upgrade_list

    def buy_upgrade(self, upgrade):
        # type: (Upgrade) -> bool
        if self.gold >= upgrade.gold_cost:
            self.gold -= upgrade.gold_cost
            self.__upgrade_list.append(upgrade)
            return True
        return False

    def get_random_reward(self, random_reward):
        # type: (RandomReward) -> None
        self.gold += random_reward.reward_gold
        self.exp += random_reward.reward_exp
        self.level_up()

    def gain_turn_reward(self):
        # type: () -> None
        self.gold += self.get_gold_per_turn()
        self.exp += self.get_exp_per_turn()
        self.level_up()

    def clone(self):
        # type: () -> Player
        return copy.deepcopy(self)


class AIPlayer(Player):
    """
    This class contains attributes of an AI controlled player as the player's opponent.
    """

    def __init__(self):
        # type: () -> None
        Player.__init__(self, "AI PLAYER")


class SavedGameData:
    """
    This class contains attributes of saved game data.
    """

    def __init__(self, player_name, start_bonus, player_data, ai_player, board):
        # type: (str, mpf, Player, AIPlayer, Board) -> None
        self.player_name: str = player_name
        self.turn: int = 0
        self.start_bonus: mpf = start_bonus
        self.player_data: Player = player_data
        self.ai_player: AIPlayer = ai_player
        self.board: Board = board

    def __str__(self):
        # type: () -> str
        res: str = ""  # initial value
        res += str(self.player_name).upper() + "\n"
        res += "Start Bonus: " + str(self.start_bonus) + "\n"
        res += "Player's stats in the game: " + str(self.player) + "\n"
        res += "CPU's stats in the game: " + str(self.cpu) + "\n"
        return res

    def clone(self):
        # type: () -> SavedGameData
        return copy.deepcopy(self)


# Creating main function used to run the game.


def main() -> int:
    """
    This main function is used to run the game.
    :return: an integer
    """

    # Saved game data
    saved_game_data: SavedGameData = SavedGameData("", mpf(random.randint(100000, 500000)),
                                                   Player(""), AIPlayer(), Board([]))  # initial value

    # The player's name
    player_name: str = ""  # initial value

    # Ollama LLM Model
    print("LLM Models:")
    for i, model in enumerate(MODELS, 1):
        print(f"{i}. {model}")

    choice: str = input("Please enter the number of the LLM model you want to use: ")
    while choice not in [str(i) for i in range(1, len(MODELS) + 1)]:
        print("Options:")
        for i, model in enumerate(MODELS, 1):
            print(f"{i}. {model}")

        choice = input("Sorry, invalid input! Please enter the number of the LLM model you want to use: ")

    chosen_model: str = MODELS[int(choice) - 1]
    output: subprocess.CompletedProcess[str] = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
    output_str: str = output.stdout
    if chosen_model not in output_str:
        print("Cannot run " + str(chosen_model) + "! Please manually pull " + str(chosen_model) + " first!")
        return 1

    llm = OllamaLLM(model=chosen_model)
    print("Enter \"NEW GAME\" to create new saved game data.")
    print("Enter \"LOAD GAME\" to load existing saved game data.")
    action: str = input("What do you want to do? ")
    while action not in ["NEW GAME", "LOAD GAME"]:
        clear()
        print("Enter \"NEW GAME\" to create new saved game data.")
        print("Enter \"LOAD GAME\" to load existing saved game data.")
        action = input("Sorry, invalid input! What do you want to do? ")

    game_started: bool = False
    while not game_started:
        if action == "NEW GAME":
            clear()

            player_name = input("Please enter player name: ")
            saved_game_files: list = [f for f in os.listdir("../saved")]
            while player_name in saved_game_files:
                print("Below is a list of existing saved game files:\n")
                for i in range(len(saved_game_files)):
                    print(str(i + 1) + ". " + str(saved_game_files[i]))

                player_name = input("Sorry, player name " + str(player_name) + " already exists! "
                                                                               "Enter another player name: ")

            # Initialising the upgrade shop.
            upgrades: list = []  # initial value.
            num_upgrades: int = random.randint(10, 20)
            for j in range(num_upgrades):
                upgrade_name: str = llm.invoke("Please enter a good name of an upgrade (safe one word response only please)!")
                upgrade_description: str = "An upgrade"
                upgrade: Upgrade = Upgrade(upgrade_name, upgrade_description, mpf("10") ** random.randint(10, 5120),
                                           mpf(random.randint(1, 2560)), mpf(random.randint(1, 2560)))
                upgrades.append(upgrade)

            upgrade_shop: UpgradeShop = UpgradeShop(upgrades)

            # Initialising the board.
            board_tiles: list = []  # Initial value
            num_tiles: int = random.randint(500, 800)
            place_count: int = 0
            for i in range(num_tiles):
                if i == 0:
                    board_tiles.append(StartTile())
                else:
                    num: int = random.randint(1, 4)
                    if num == 1:
                        board_tiles.append(EmptySpace())
                    elif num == 2:
                        place_name: str = llm.invoke("Please enter a name of a jungle, mountain, pirate cove, lake, forest, "
                                           "desert, harbor, sea, castle, island, or beach (include the place name only please)!")
                        place_description: str = "A " + str(random.choice(["jungle", "mountain", "pirate cove",
                                                                           "lake", "forest", "desert", "harbor", "sea",
                                                                           "castle", "island", "beach"]))
                        place_gold_cost: mpf = mpf("10") ** random.randint(5, 2000)
                        place: Place = Place(place_name, place_description, place_gold_cost,
                                             place_gold_cost / mpf("1e3"), place_gold_cost / mpf("1e5"))
                        board_tiles.append(place)
                        place_count += 1
                        clear()
                        print(str(place_count) + " places generated!")
                    elif num == 3:
                        board_tiles.append(RandomRewardTile())
                    elif num == 4:
                        board_tiles.append(upgrade_shop)

            board: Board = Board(board_tiles)
            saved_game_data = SavedGameData(player_name, mpf(random.randint(100000, 500000)), Player(player_name),
                                            AIPlayer(), board)
            game_started = True
        else:
            clear()

            saved_game_files: list = [f for f in os.listdir("../saved")]
            if len(saved_game_files) == 0:
                action = "NEW GAME"

            print("Below is a list of existing saved game files:\n")
            for i in range(len(saved_game_files)):
                print(str(i + 1) + ". " + str(saved_game_files[i]))

            player_name = input("Please enter player name associated with saved game data you want to load: ")
            while player_name not in saved_game_files:
                clear()
                print("Below is a list of existing saved game files:\n")
                for i in range(len(saved_game_files)):
                    print(str(i + 1) + ". " + str(saved_game_files[i]))

                player_name = input("Sorry, invalid input! Please enter player name associated with "
                                    "saved game data you want to load: ")

            saved_game_data = load_game_data(os.path.join("../saved", player_name))
            game_started = True

    # Start playing the game
    while True:
        clear()
        print("Enter \"Y\" for yes.")
        print("Enter anything else for no.")
        continue_playing: str = input("Do you want to continue playing? ")
        if continue_playing != "Y":
            save_game_data(saved_game_data, os.path.join("../saved", player_name))
            return 0  # successfully saved the game

        clear()

        # Incrementing the value of new_game.turn
        saved_game_data.turn += 1

        print("Your stats:\n\n" + str(saved_game_data.player_data))
        print("CPU's stats:\n\n" + str(saved_game_data.ai_player))

        # Checking whether it is player's or AI player's turn
        if saved_game_data.turn % 2 == 1:
            saved_game_data.player_data.gain_turn_reward()
            print("It is your turn to roll the dice!")
            print("Enter 'ROLL' to roll the dice.")
            print("Enter anything else to save game data and quit the game.")
            action: str = input("What do you want to do? ")
            if action == "ROLL":
                saved_game_data.player_data.roll_dice(saved_game_data)
                curr_tile: Tile = saved_game_data.board.get_tiles()[saved_game_data.player_data.location]
                print("You are now at " + str(curr_tile.name) + "!")
                if isinstance(curr_tile, StartTile) or isinstance(curr_tile, EmptySpace):
                    pass  # do nothing
                elif isinstance(curr_tile, Place):
                    if curr_tile.owner is None:
                        # Ask the player whether he/she wants to buy the place or not.
                        print("Enter 'Y' for yes.")
                        print("Enter anything else for no.")
                        buy_place: str = input("Do you want to buy " + str(curr_tile.name) + " for "
                                               + str(curr_tile.gold_cost) + " gold? ")
                        if buy_place == "Y":
                            if saved_game_data.player_data.buy_place(curr_tile):
                                print("Congratulations! You have successfully bought " + str(curr_tile.name) + "!")
                            else:
                                print("Sorry! You have insufficient gold!")

                    elif curr_tile in saved_game_data.player_data.get_owned_list():
                        # Ask the player whether he/she wants to upgrade the place or not.
                        print("Enter 'Y' for yes.")
                        print("Enter anything else for no.")
                        upgrade_place: str = input("Do you want to upgrade " + str(curr_tile.name) + "? ")
                        if upgrade_place == "Y":
                            if saved_game_data.player_data.upgrade_place(curr_tile):
                                print("Congratulations! You have successfully upgraded " + str(curr_tile.name) + "!")
                            else:
                                print("Sorry! You have insufficient gold!")
                    else:
                        # Ask the player whether he/she wants to acquire the place or not.
                        print("Enter 'Y' for yes.")
                        print("Enter anything else for no.")
                        acquire_place: str = input("Do you want to acquire " + str(curr_tile.name) + "? ")
                        if acquire_place == "Y":
                            if saved_game_data.player_data.acquire_place(curr_tile, curr_tile.owner):
                                print("Congratulations! You have successfully acquired " + str(curr_tile.name) + "!")
                            else:
                                print("Sorry! You have insufficient gold!")

                elif isinstance(curr_tile, RandomRewardTile):
                    # Grant random reward
                    random_reward: RandomReward = RandomReward()
                    saved_game_data.player_data.get_random_reward(random_reward)
                    print("Congratulations! You earned " + str(random_reward.reward_gold) + " gold and "
                          + str(random_reward.reward_exp) + " EXP!")

                elif isinstance(curr_tile, UpgradeShop):
                    # Asking whether the player wants to buy an upgrade or not.
                    print("Enter 'Y' for yes.")
                    print("Enter anything else for no.")
                    buy_upgrade: str = input("Do you want to buy an upgrade? ")

                    if buy_upgrade == "Y":
                        # Asking the player to choose which upgrade to buy.
                        print("Below is a list of upgrades sold in the upgrade shop.")
                        upgrade_index: int = 1  # initial value
                        for upgrade in curr_tile.get_upgrades_sold():
                            print("UPGRADE #" + str(upgrade_index))
                            print(str(upgrade) + "\n")
                            upgrade_index += 1

                        buy_upgrade_index: int = int(input("Please enter the index of the upgrade "
                                                           "you want to buy (1 - " +
                                                           str(len(curr_tile.get_upgrades_sold())) + "): "))
                        while buy_upgrade_index < 1 or buy_upgrade_index > len(curr_tile.get_upgrades_sold()):
                            buy_upgrade_index = int(input("Sorry, invalid input! Please enter the index of the upgrade "
                                                          "you want to buy (1 - " +
                                                          str(len(curr_tile.get_upgrades_sold())) + "): "))

                        upgrade_to_buy: Upgrade = curr_tile.get_upgrades_sold()[buy_upgrade_index - 1]
                        if saved_game_data.player_data.buy_upgrade(upgrade_to_buy):
                            print("Congratulations! You have successfully bought " + str(upgrade_to_buy.name) + "!")
                        else:
                            print("Sorry! You have insufficient gold!")

                else:
                    pass  # do nothing
            else:
                break
        else:
            saved_game_data.ai_player.gain_turn_reward()
            print("It is CPU's turn to roll the dice!")
            saved_game_data.ai_player.roll_dice(saved_game_data)
            curr_tile: Tile = saved_game_data.board.get_tiles()[saved_game_data.ai_player.location]
            print("CPU is now at " + str(curr_tile.name) + "!")
            if isinstance(curr_tile, StartTile) or isinstance(curr_tile, EmptySpace):
                pass  # do nothing
            elif isinstance(curr_tile, Place):
                if curr_tile.owner is None:
                    buy_place: bool = random.random() <= 0.75
                    if buy_place:
                        saved_game_data.ai_player.buy_place(curr_tile)

                elif curr_tile in saved_game_data.ai_player.get_owned_list():
                    upgrade_place: bool = random.random() <= 0.75
                    if upgrade_place:
                        saved_game_data.ai_player.upgrade_place(curr_tile)
                else:
                    acquire_place: bool = random.random() <= 0.75
                    if acquire_place:
                        saved_game_data.ai_player.acquire_place(curr_tile, curr_tile.owner)

            elif isinstance(curr_tile, RandomRewardTile):
                # Grant random reward
                random_reward: RandomReward = RandomReward()
                saved_game_data.ai_player.get_random_reward(random_reward)
                print("CPU earned " + str(random_reward.reward_gold) + " gold and "
                      + str(random_reward.reward_exp) + " EXP!")

            elif isinstance(curr_tile, UpgradeShop):
                buy_upgrade: bool = random.random() <= 0.75
                if buy_upgrade:
                    buy_upgrade_index: int = random.randint(1, len(curr_tile.get_upgrades_sold()))
                    upgrade_to_buy: Upgrade = curr_tile.get_upgrades_sold()[buy_upgrade_index - 1]
                    saved_game_data.ai_player.buy_upgrade(upgrade_to_buy)
            else:
                pass  # do nothing


if __name__ == "__main__":
    main()
