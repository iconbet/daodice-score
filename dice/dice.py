from iconservice import *

TAG = "DICE"
DEBUG = True
UPPER_LIMIT = 99
LOWER_LIMIT = 0
MAIN_BET_MULTIPLIER = 98.5
SIDE_BET_MULTIPLIER = 95
BET_MIN = 100000000000000000
SIDE_BET_TYPES = ["digits_match", "icon_logo1", "icon_logo2"]
SIDE_BET_MULTIPLIERS = {"digits_match": 9.5, "icon_logo1": 5, "icon_logo2": 95}
BET_LIMIT_RATIOS_SIDE_BET = {"digits_match": 1140, "icon_logo1": 540, "icon_logo2": 12548}


# An interface to roulette score
class RouletteInterface(InterfaceScore):
    @interface
    def get_treasury_min(self) -> int:
        pass

    @interface
    def take_wager(self, _amount: int) -> None:
        pass

    @interface
    def wager_payout(self, _payout: int) -> None:
        pass


class Dice(IconScoreBase):
    _GAME_ON = "game_on"
    _ROULETTE_SCORE = 'roulette_score'

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        if DEBUG is True:
            Logger.debug(f'In __init__.', TAG)
            Logger.debug(f'owner is {self.owner}.', TAG)
        self._game_on = VarDB(self._GAME_ON, db, value_type=bool)
        self._roulette_score = VarDB(self._ROULETTE_SCORE, db, value_type=Address)

    @eventlog(indexed=3)
    def BetPlaced(self, amount: int, upper: int, lower: int):
        pass

    @eventlog(indexed=2)
    def BetSource(self, _from: Address, timestamp: int):
        pass

    @eventlog(indexed=3)
    def PayoutAmount(self, payout: int, main_bet_payout: int, side_bet_payout: int):
        pass

    @eventlog(indexed=3)
    def BetResult(self, spin: str, winningNumber: int, payout: int):
        pass

    @eventlog(indexed=2)
    def FundTransfer(self, recipient: Address, amount: int, note: str):
        pass

    def on_install(self) -> None:
        super().on_install()
        self._game_on.set(False)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_score_owner(self) -> Address:
        """
        A function to return the owner of this score.
        :return: Owner address of this score
        :rtype: :class:`iconservice.base.address.Address`
        """
        return self.owner

    @external
    def set_roulette_score(self, _score: Address) -> None:
        """
        Sets the roulette score address. The function can only be invoked by score owner.
        :param _score: Score address of the roulette
        :type _score: :class:`iconservice.base.address.Address`
        """
        if self.msg.sender == self.owner:
            self._roulette_score.set(_score)

    @external(readonly=True)
    def get_roulette_score(self) -> Address:
        """
        Returns the roulette score address.
        :return: Address of the roulette score
        :rtype: :class:`iconservice.base.address.Address`
        """
        return self._roulette_score.get()

    @external
    def game_on(self) -> None:
        """
        Set the status of game as on. Only the owner of the game can call this method. Owner must have set the
        roulette score before changing the game status as on.
        """
        if self.msg.sender != self.owner:
            revert('Only the owner can call the game_on method')
        if not self._game_on.get() and self._roulette_score.get() is not None:
            self._game_on.set(True)

    @external
    def game_off(self) -> None:
        """
        Set the status of game as off. Only the owner of the game can call this method.
        """
        if self.msg.sender != self.owner:
            revert('Only the owner can call the game_on method')
        if self._game_on.get():
            self._game_on.set(False)

    @external(readonly=True)
    def get_game_on(self) -> bool:
        """
        Returns the current game status
        :return: Current game status
        :rtype: bool
        """
        return self._game_on.get()

    @external(readonly=True)
    def get_side_bet_multipliers(self) -> dict:
        """
        Returns the side bet multipliers. Side bets are matching digits, single icon logo and double icon logo.
        :return: Side bet multipliers
        :rtype: dict
        """
        return SIDE_BET_MULTIPLIERS

    @external
    def untether(self) -> None:
        """
        A function to redefine the value of  self.owner once it is possible .
        To  be included through an update if it is added to ICONSERVICE
        Sets the value of self.owner to the score holding the game treasury
        """
        if self.msg.sender != self.owner:
            revert('Only the owner can call the untether method ')
        pass

    def get_random(self, user_seed: str = '') -> float:
        """
       Generates a random # from tx hash, block timestamp and user provided
       seed. The block timestamp provides the source of unpredictability.
       :param user_seed: 'Lucky phrase' provided by user, defaults to ""
       :type user_seed: str,optional
       :return: Number from [x / 100000.0 for x in range(100000)]
       :rtype: float
       """
        Logger.debug(f'Entered get_random.', TAG)
        if self.msg.sender.is_contract:
            revert("ICONbet: SCORE cant play games")
        seed = (str(bytes.hex(self.tx.hash)) + str(self.now()) + user_seed)
        spin = (int.from_bytes(sha3_256(seed.encode()), "big") % 100000) / 100000.0
        Logger.debug(f'Result of the spin was {spin}.', TAG)
        return spin

    @payable
    @external
    def call_bet(self, upper: int, lower: int, user_seed: str = '', side_bet_amount: int = 0,
                 side_bet_type: str = '') -> None:
        """
        Main bet function. It takes the upper and lower number for bet. Upper and lower number must be in the range
        [0,99]. The difference between upper and lower can be in the range of [0,95].
        :param upper: Upper number user can bet. It must be in the range [0,99]
        :type upper: int
        :param lower: Lower number user can bet. It must be in the range [0,99]
        :type lower: int
        :param user_seed: 'Lucky phrase' provided by user, defaults to ""
        :type user_seed: str,optional
        :param side_bet_amount: Amount to be used for side bet from value sent to this function, defaults to 0
        :type side_bet_amount: int,optional
        :param side_bet_type: side bet types can be one of this ["digits_match", "icon_logo1","icon_logo2"], defaults to
         ""
        :type side_bet_type: str,optional
        """
        return self.__bet(upper, lower, user_seed, side_bet_amount, side_bet_type)

    def __bet(self, upper: int, lower: int, user_seed: str, side_bet_amount: int, side_bet_type: str) -> None:
        side_bet_win = False
        side_bet_set = False
        side_bet_payout = 0
        self.BetSource(self.tx.origin, self.tx.timestamp)

        roulette_score = self.create_interface_score(self._roulette_score.get(), RouletteInterface)
        _treasury_min = roulette_score.get_treasury_min()
        self.icx.transfer(self._roulette_score.get(), self.msg.value)
        self.FundTransfer(self._roulette_score.get(), self.msg.value, "Sending icx to Roulette")
        roulette_score.take_wager(self.msg.value)
        if not self._game_on.get():
            Logger.debug(f'Game not active yet.', TAG)
            revert(f'Game not active yet.')
        if not (0 <= upper <= 99 and 0 <= lower <= 99):
            Logger.debug(f'Numbers placed with out of range numbers', TAG)
            revert(f'Invalid bet. Choose a number between 0 to 99')
        if not (0 <= upper - lower <= 95):
            Logger.debug(f'Bet placed with illegal gap', TAG)
            revert(f'Invalid gap. Choose upper and lower values such that gap is between 0 to 95')
        if (side_bet_type == '' and side_bet_amount != 0) or (side_bet_type != '' and side_bet_amount == 0):
            Logger.debug(f'should set both side bet type as well as side bet amount', TAG)
            revert(f'should set both side bet type as well as side bet amount')
        if side_bet_amount < 0:
            revert(f'Bet amount cannot be negative')
        if side_bet_type != '' and side_bet_amount != 0:
            side_bet_set = True
            if side_bet_type not in SIDE_BET_TYPES:
                Logger.debug(f'Invalid side bet type', TAG)
                revert(f'Invalid side bet type.')
            side_bet_limit = _treasury_min // BET_LIMIT_RATIOS_SIDE_BET[side_bet_type]
            if side_bet_amount < BET_MIN or side_bet_amount > side_bet_limit:
                Logger.debug(f'Betting amount {side_bet_amount} out of range.', TAG)
                revert(f'Betting amount {side_bet_amount} out of range ({BET_MIN} ,{side_bet_limit}).')
            side_bet_payout = int(SIDE_BET_MULTIPLIERS[side_bet_type] * 100) * side_bet_amount // 100
        main_bet_amount = self.msg.value - side_bet_amount
        self.BetPlaced(main_bet_amount, upper, lower)
        gap = (upper - lower) + 1
        if main_bet_amount == 0:
            Logger.debug(f'No main bet amount provided', TAG)
            revert(f'No main bet amount provided')

        main_bet_limit = (_treasury_min * 1.5 * gap) // (68134 - 681.34 * gap)
        if main_bet_amount < BET_MIN or main_bet_amount > main_bet_limit:
            Logger.debug(f'Betting amount {main_bet_amount} out of range.', TAG)
            revert(f'Main Bet amount {main_bet_amount} out of range {BET_MIN},{main_bet_limit} ')
        main_bet_payout = int(MAIN_BET_MULTIPLIER * 100) * main_bet_amount // (100 * gap)
        payout = side_bet_payout + main_bet_payout
        if self.icx.get_balance(self._roulette_score.get()) < payout:
            Logger.debug(f'Not enough in treasury to make the play.', TAG)
            revert('Not enough in treasury to make the play.')
        spin = self.get_random(user_seed)
        winningNumber = int(spin * 100)
        Logger.debug(f'winningNumber was {winningNumber}.', TAG)
        if lower <= winningNumber <= upper:
            main_bet_win = True
        else:
            main_bet_win = False
        if side_bet_set:
            side_bet_win = self.check_side_bet_win(side_bet_type, winningNumber)
            if not side_bet_win:
                side_bet_payout = 0
        main_bet_payout = main_bet_payout * main_bet_win
        payout = main_bet_payout + side_bet_payout
        self.BetResult(str(spin), winningNumber, payout)
        self.PayoutAmount(payout, main_bet_payout, side_bet_payout)
        if main_bet_win or side_bet_win:
            Logger.debug(f'Amount owed to winner: {payout}', TAG)
            try:
                Logger.debug(f'Trying to send to ({self.tx.origin}): {payout}.', TAG)
                roulette_score.wager_payout(payout)
                Logger.debug(f'Sent winner ({self.tx.origin}) {payout}.', TAG)
            except BaseException as e:
                Logger.debug(f'Send failed. Exception: {e}', TAG)
                revert('Network problem. Winnings not sent. Returning funds.')
        else:
            Logger.debug(f'Player lost. ICX retained in treasury.', TAG)

    # check for bet limits and side limits
    def check_side_bet_win(self, side_bet_type: str, winning_number: int) -> bool:
        """
        Checks the conditions for side bets are matched or not.
        :param side_bet_type: side bet types can be one of this ["digits_match", "icon_logo1","icon_logo2"], defaults to
         ""
        :type side_bet_type: str,optional
        :param winning_number: winning number returned by random function
        :type winning_number: int
        :return: Returns true or false based on the side bet type and the winning number
        :rtype: bool
        """
        if side_bet_type == SIDE_BET_TYPES[0]:  # digits_match
            return winning_number % 11 == 0
        elif side_bet_type == SIDE_BET_TYPES[1]:  # for icon logo1 ie for numbers having 1 zero in it
            return str(0) in str(winning_number) or winning_number in range(1, 10)
        elif side_bet_type == SIDE_BET_TYPES[2]:  # for icon logo2 ie for 0
            return winning_number == 0
        else:
            return False

    @payable
    def fallback(self):
        pass
