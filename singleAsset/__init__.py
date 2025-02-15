from otree.api import *
import time
import random
import numpy as np
from operator import itemgetter
from ast import literal_eval

doc = """Continuous double auction market"""

class C(BaseConstants):
    NAME_IN_URL = 'sCDA'
    PLAYERS_PER_GROUP = None
    num_trial_rounds = 1
    NUM_ROUNDS = 4  ## incl. trial periods
    base_payment = cu(10)
    multiplier = 90
    min_payment_in_round = cu(0)
    min_payment = cu(4)
    FV = 10
    num_assets = 15
    decimals = 2
    marketTime = 210  # needed to initialize variables but exchanged by session_config

    n_periods = NUM_ROUNDS - num_trial_rounds
    dividend_per_period = FV / n_periods #valor del divdendos que deberia recibir por periodo
    dividend_values = [dividend_per_period] * n_periods  # Lista con n dividendos

    # 5 valores posibles de dividendos alrededor de dividend_per_period
    dividend_values = [
        round(dividend_per_period * 0.6, decimals),  # 60% del valor esperado
        round(dividend_per_period * 0.85, decimals), # 85%
        round(dividend_per_period * 1.0, decimals),  # 100% (valor esperado)
        round(dividend_per_period * 1.15, decimals), # 115%
        round(dividend_per_period * 1.4, decimals)   # 140%
    ]

    # Probabilidades asignadas para que la media sea dividend_per_period
    probabilities = [0.1, 0.2, 0.4, 0.2, 0.1]  # Deben sumar 1

class Subsession(BaseSubsession):
    offerID = models.IntegerField(initial=0)
    orderID = models.IntegerField(initial=0)
    transactionID = models.IntegerField(initial=0)

class Dividend(ExtraModel):
    dividendId = models.FloatField()
    amount = models.FloatField()

def vars_for_admin_report(subsession):
    # this function defines the values sent to the admin report page
    groups = subsession.get_groups()
    period = subsession.round_number
    payoffs = sorted([p.payoff for p in subsession.get_players()])
    market_times = sorted([g.marketTime for g in groups])
    highcharts_series = []
    trades = [{'x': tx.transactionTime, 'y': tx.price, 'name': 'Trades'} for tx in Transaction.filter() if tx.Period == period and tx.group in groups]
    highcharts_series.append({'name': 'Trades', 'data': trades, 'type': 'scatter', 'id': 'trades', 'marker': {'symbol': 'circle'}})
    bids = [{'x': bx.BATime, 'y': bx.bestBid, 'name': 'Bids'} for bx in BidAsks.filter() if bx.Period == period and bx.BATime and bx.bestBid]
    highcharts_series.append({'name': 'Bids', 'data': bids, 'type': 'line', 'id': 'bids', 'lineWidth': 2})
    asks = [{'x': ax.BATime, 'y': ax.bestAsk, 'name': 'Asks'} for ax in BidAsks.filter() if ax.Period == period and ax.BATime and ax.bestAsk]
    highcharts_series.append({'name': 'Asks', 'data': asks, 'type': 'line', 'id': 'bids', 'lineWidth': 2})
    return dict(
        marketTimes=market_times,
        payoffs=payoffs,
        series=highcharts_series,
    )



class Group(BaseGroup):
    #average_price = models.FloatField()  # average round price

    marketTime = models.FloatField(initial=C.marketTime)
    marketStartTime = models.FloatField()
    marketEndTime = models.FloatField()
    randomisedTypes = models.BooleanField()

    numAssets = models.IntegerField(initial=0)
    numParticipants = models.IntegerField(initial=0)
    numActiveParticipants = models.IntegerField(initial=0)
    assetNames = models.LongStringField()
    aggAssetsValue = models.FloatField()
    assetValue = models.FloatField()
    assetsInRound = models.LongStringField() #ojo

    
    bestAsk = models.FloatField()
    bestBid = models.FloatField()
    transactions = models.IntegerField(initial=0, min=0)
    marketBuyOrders = models.IntegerField(initial=0, min=0)
    marketSellOrders = models.IntegerField(initial=0, min=0)
    transactedVolume = models.IntegerField(initial=0, min=0)
    marketBuyVolume = models.IntegerField(initial=0, min=0)
    marketSellVolume = models.IntegerField(initial=0, min=0)
    limitOrders = models.IntegerField(initial=0, min=0)
    limitBuyOrders = models.IntegerField(initial=0, min=0)
    limitSellOrders = models.IntegerField(initial=0, min=0)
    limitVolume = models.IntegerField(initial=0, min=0)
    limitBuyVolume = models.IntegerField(initial=0, min=0)
    limitSellVolume = models.IntegerField(initial=0, min=0)
    cancellations = models.IntegerField(initial=0, min=0)
    cancelledVolume = models.IntegerField(initial=0, min=0)


    numDividends = models.IntegerField(initial=0)
    dividentValue = models.FloatField()

def random_types(group: Group):
    # this code is run at the first WaitToStart page when all participants arrived
    # this function returns a binary variable to the group table whether roles should be randomised between periods.
    return group.session.config['randomise_types']


def assign_types(group: Group):
    # this code is run at the first WaitToStart page, within the initiate_group() function, when all participants arrived
    # this function allocates traders' types at the beginning of the session or when randomised.
    players = group.get_players()
    if group.randomisedTypes or Subsession.round_number == 1:
        ii = group.numParticipants  # number of traders without type yet
        role_structure = {'observer': 0, 'trader': ii}
        for r in ['observer', 'trader']:  # for each role
            k = 0  # number of players assigned this role
            max_k = role_structure[r]  # number of players to be assigned with this role
            while k < max_k and ii > 0:  # until enough role 'r' types are assigned
                rand_num = round(random.uniform(a=0, b=1) * ii, 0)
                i = 0
                for p in players:
                    if p.isParticipating and i < rand_num and not p.field_maybe_none('roleID'):
                        i += 1
                        if rand_num == i:
                            ii -= 1
                            p.roleID = str(r)
                            p.participant.vars['roleID'] = str(r)
                            k += 1
                    if not p.isParticipating and not p.field_maybe_none('roleID'):
                        p.roleID = str('not participating')
                        p.participant.vars['roleID'] = str('not participating')
    else:
        for p in players:
            p.roleID = p.participant.vars['roleID']

#def define_assets_in_round(group: Group):
  #  assetsInRound = C.num_assets * group.numParticipants 
   # return assetsInRound

def define_asset_value(group: Group):
    # this code is run at the first WaitToStart page, within the initiate_group() function, when all participants arrived
    # this function determines the BBV and shares the information to the players table.

    asset_value = round(C.FV, C.decimals)
    if asset_value is None:
        print("[ERROR] El valor del activo no fue inicializado correctamente")
        asset_value = 10  # Valor de respaldo en caso de error
    group.assetValue = asset_value

def count_participants(group: Group):
    # this code is run at the first WaitToStart page, within the initiate_group() function, when all participants arrived
    # this function determines the number of actual participants.
    if group.round_number == 1:
        for p in group.get_players():
            if p.isParticipating == 1:
                group.numParticipants += 1
    else:  # since player.isParticipating is not newly assign with a value by a click or a timeout, I take the value from the previous round
        for p in group.get_players():
            pr = p.in_round(group.round_number - 1)
            p.isParticipating = pr.isParticipating
        group.numParticipants = group.session.vars['numParticipants']
    group.session.vars['numParticipants'] = group.numParticipants



def initiate_group(group: Group):
    # this code is run at the first WaitToStart page when all participants arrived
    # this function starts substantial calculations on group level.
    count_participants(group=group)
    define_asset_value(group=group)
    assign_types(group=group)



def get_max_time(group: Group):
    # this code is run at the WaitingMarket page just before the market page when all participants arrived
    # this function returns the duration time of a market.
    return group.session.config['market_time']  # currently the binary value is retrieved from the config variables


class Player(BasePlayer):
    isParticipating = models.BooleanField(choices=((True, 'active'), (False, 'inactive')), initial=0)  ## describes whether this participant is participating in this round, i.e., whether they pressed the 'next' button.
    isObserver = models.BooleanField(choices=((True, 'active'), (False, 'inactive')), initial=0)  ## describes a participant role as active trader or observer
    roleID = models.StringField()
    allowShort = models.BooleanField(initial=True)
    allowLong = models.BooleanField(initial=True)
    assetValue = models.FloatField(initial=0)
    initialCash = models.FloatField(initial=0, decimal=C.decimals)
    initialAssets = models.IntegerField(initial=0)
    initialEndowment = models.FloatField(initial=0, decimal=C.decimals)
    cashHolding = models.FloatField(initial=0, decimal=C.decimals)
    assetsHolding = models.IntegerField(initial=0)
    endEndowment = models.FloatField(initial=0, decimal=C.decimals)
    capLong = models.FloatField(initial=0, min=0, decimal=C.decimals)
    capShort = models.IntegerField(initial=0, min=0)
    transactions = models.IntegerField(initial=0, min=0)
    marketOrders = models.IntegerField(initial=0, min=0)
    marketBuyOrders = models.IntegerField(initial=0, min=0)
    marketSellOrders = models.IntegerField(initial=0, min=0)
    transactedVolume = models.IntegerField(initial=0, min=0)
    marketOrderVolume = models.IntegerField(initial=0, min=0)
    marketBuyVolume = models.IntegerField(initial=0, min=0)
    marketSellVolume = models.IntegerField(initial=0, min=0)
    limitOrders = models.IntegerField(initial=0, min=0)
    limitBuyOrders = models.IntegerField(initial=0, min=0)
    limitSellOrders = models.IntegerField(initial=0, min=0)
    limitVolume = models.IntegerField(initial=0, min=0)
    limitBuyVolume = models.IntegerField(initial=0, min=0)
    limitSellVolume = models.IntegerField(initial=0, min=0)
    limitOrderTransactions = models.IntegerField(initial=0, min=0)
    limitBuyOrderTransactions = models.IntegerField(initial=0, min=0)
    limitSellOrderTransactions = models.IntegerField(initial=0, min=0)
    limitVolumeTransacted = models.IntegerField(initial=0, min=0)
    limitBuyVolumeTransacted = models.IntegerField(initial=0, min=0)
    limitSellVolumeTransacted = models.IntegerField(initial=0, min=0)
    cancellations = models.IntegerField(initial=0, min=0)
    cancelledVolume = models.IntegerField(initial=0, min=0)
    cashOffered = models.FloatField(initial=0, min=0, decimal=C.decimals)
    assetsOffered = models.IntegerField(initial=0, min=0)
    tradingProfit = models.FloatField(initial=0)
    wealthChange = models.FloatField(initial=0)
    finalPayoff = models.CurrencyField(initial=0)
    selectedRound = models.IntegerField(initial=1)

    # Dividend Management
    initialDividend = models.FloatField(initial=0) 
    dividendHolding = models.FloatField(initial=0) 
    dividendByAsset = models.FloatField(initial=0)  # ✅

def generate_dividends(player: Player):
    return float(np.random.choice(C.dividend_values, p=C.probabilities))# Seleccionar un dividendo aleatorio basado en la configuración global


def asset_endowment(player: Player):
    # this code is run at the first WaitToStart page, within the initiate_player() function, when all participants arrived
    # this function returns a participant's initial asset endowment
    return C.num_assets


def short_allowed(player: Player):
    # this code is run at the first WaitToStart page, within the initiate_player() function, when all participants arrived
    # this function returns a binary variable whether short selling is allowed
    group = player.group
    return group.session.config['short_selling']  # currently the binary value is retrieved from the config variables


def long_allowed(player: Player):
    # this code is run at the first WaitToStart page, within the initiate_player() function, when all participants arrived
    # this function returns a binary variable whether buying on margin is allowed
    group = player.group
    return group.session.config['margin_buying']  # currently the binary value is retrieved from the config variables


def asset_short_limit(player: Player):
    # this code is run at the first WaitToStart page, within the initiate_player() function, when all participants arrived
    # this function returns a participant's short selling limits if that is allowed
    if player.allowShort:
        return player.initialAssets  # currently the short selling limit is set equal to the asset endowment
    else:
        return 0


def cash_endowment(player: Player):
    # this code is run at the first WaitToStart page, within the initiate_player() function, when all participants arrived
    # this function returns a participant's initial cash endowment
    group = player.group
    return float(round(C.num_assets * group.assetValue, C.decimals))  ## the multiplication with the asset value garanties a cash to asset ratio of 1 in the market


def cash_long_limit(player: Player):
    # this code is run at the first WaitToStart page, within the initiate_player() function, when all participants arrived
    # this function returns a participant's buying on margin limits if that is allowed
    if player.allowLong:
        return player.initialCash  # currently the buying on margin limit is set equal to the cash endowment
    else:
        return 0


def assign_role_attr(player: Player, role_id):
    # this code is run at the first WaitToStart page, within the set_player() function, when all participants arrived
    # this function determines a participant's attributes in terms of being active or observer, and distributes information
    if role_id == 'observer':
        player.participant.vars['isObserver'] = True
    elif role_id == 'trader':
        player.participant.vars['isObserver'] = False



def initiate_player(player: Player):
    # this code is run at the first WaitToStart page when all participants arrived
    # this function starts substantial calculations on player level.
    group = player.group
    if not player.isObserver and player.isParticipating:
        initial_cash = cash_endowment(player=player)
        player.initialCash = initial_cash
        player.cashHolding = initial_cash
        player.allowLong = long_allowed(player=player)
        player.capLong = cash_long_limit(player=player)
        initial_assets = asset_endowment(player=player)
        player.initialAssets = initial_assets
        group.numAssets += player.initialAssets
        player.assetsHolding = initial_assets
        player.allowShort = short_allowed(player=player)
        player.capShort = asset_short_limit(player=player)

        initial_dividends = generate_dividends(player=player)
        player.initialDividend = initial_dividends
        player.dividendHolding = initial_dividends

def store_player_financials(player: Player):
    """ Guarda o reinicia los valores financieros del jugador según el periodo de prueba """
    group = player.group

    # 🔴 Si es la primera ronda después del periodo de prueba, reiniciar valores
    if player.round_number == C.num_trial_rounds + 1:
        initiate_player(player)
        #print(f"\n🔄 [RESET FINANCIALS] Jugador {player.id_in_group} - Ronda {group.round_number} (Nueva fase)")
    elif player.round_number > 1:  # 🔴 Evitar error en la ronda 1
        # 🔵 Si no es el inicio de una nueva fase, continuar con los valores previos
        prev_player = player.in_round(player.round_number - 1)

        player.initialCash = prev_player.initialCash
        player.initialAssets = prev_player.initialAssets
        player.assetsHolding = prev_player.assetsHolding
        player.initialDividend = generate_dividends(player)
        player.dividendHolding = prev_player.dividendHolding + player.initialDividend
        player.capLong = prev_player.capLong
        player.capShort = prev_player.capShort
        player.allowLong = prev_player.allowLong
        player.allowShort = prev_player.allowShort

        # ✅ Nuevo cálculo de dividendos obtenidos por activo
        player.dividendByAsset = player.initialDividend * player.assetsHolding
        player.cashHolding = prev_player.cashHolding + player.dividendByAsset
        print(f"💰 [CASH UPDATE] Jugador {player.id_in_group} - Ronda {player.round_number}")
        print(f"  - Dinero Final (cashHolding): {player.cashHolding:.2f}")
        if player.round_number == C.num_trial_rounds + 1:
            print("🔄 [RESET] Reiniciando valores financieros después de la prueba.")
            initiate_player(player)

def set_player(player: Player):
    # this code is run at the first WaitToStart page when all participants arrived.
    # this function retrieves player characteristics from the participants table.
    assign_role_attr(player=player, role_id=player.field_maybe_none('roleID'))
    if player.isParticipating:
        player.isObserver = player.participant.vars['isObserver']


def live_method(player: Player, data):
    group = player.group
    key = data.get('operationType')

    # this code is run at the market page whenever a participants updates the page or a new order is created.
    # this function receives orders and processes them, furthermore, it sends the new order book to participant.
    if not data or 'operationType' not in data:
        return
    key = data['operationType']
    highcharts_series = []
    group = player.group
    period = group.round_number
    players = group.get_players()
    if key == 'limit_order':
        limit_order(player, data)
    elif key == 'cancel_limit':
        cancel_limit(player, data)
    elif key == 'market_order':
        transaction(player, data)
        store_group_transactions(group)  # ✅ Guardar las transacciones en `GroupTransactions`

    offers = Limit.filter(group=group)
    transactions = get_session_transactions(group)  # 🔥 Recuperar transacciones acumuladas
    if transactions:
        hc_data = [{'x': tx['time'], 'y': tx['price'], 'name': 'Trades'} for tx in transactions]
        highcharts_series.append({'name': 'Trades', 'data': hc_data, 'type': 'scatter', 'id': 'trades', 'marker': {'symbol': 'circle'}})
    else:
        highcharts_series = []

    best_bid = group.field_maybe_none('bestBid')
    best_ask = group.field_maybe_none('bestAsk')
    BidAsks.create(  # observe Bids and Asks of respective asset before the request
        group=group,
        Period=period,
        orderID=group.subsession.orderID,
        bestBid=best_bid,
        bestAsk=best_ask,
        BATime=round(float(time.time() - player.group.marketStartTime), C.decimals),
        timing='before',
        operationType=key,
    )
    bids = sorted([[offer.price, offer.remainingVolume, offer.offerID, offer.makerID] for offer in offers if offer.isActive and offer.isBid], reverse=True, key=itemgetter(0))
    asks = sorted([[offer.price, offer.remainingVolume, offer.offerID, offer.makerID] for offer in offers if offer.isActive and not offer.isBid], key=itemgetter(0))
    msgs = News.filter(group=group)
    if asks:
        best_ask = asks[0][0]
        group.bestAsk = best_ask
    else:
        best_ask = None
    if bids:
        best_bid = bids[0][0]
        group.bestBid = best_bid
    else:
        best_bid = None
    BidAsks.create(  # observe Bids and Asks of respective asset after the request
        group=group,
        Period=period,
        orderID=group.subsession.orderID,
        bestBid=best_bid,
        bestAsk=best_ask,
        BATime=round(float(time.time() - player.group.marketStartTime), C.decimals),
        timing='after',
        operationType=key,
    )
    if key == 'market_start':
        players = [player]
    print(f"📊 [POST-TRADE] {player.id_in_group}: Cash={player.cashHolding}, Activos={player.assetsHolding}")
    return {  # the next lines define the information send to participants
        p.id_in_group: dict(
            bids=bids,
            asks=asks,
            trades = sorted(
                [[t["price"], t["volume"], t["time"], t["sellerID"]] 
                for t in transactions if (t["buyerID"] == p.id_in_group or t["sellerID"] == p.id_in_group)], 
                reverse=True, key=itemgetter(2)
            ),
            cashHolding=p.cashHolding,
            assetsHolding=p.assetsHolding,
            dividendHolding= p.dividendHolding,
            highcharts_series=highcharts_series,
            news=sorted([[m.msg, m.msgTime, m.playerID] for m in msgs if m.playerID == p.id_in_group], reverse=True, key=itemgetter(1))
        )
        for p in players
    }


def calc_round_profit(player: Player):
    group = player.group
    """ Calcula la ganancia del jugador en la ronda actual. """
    # Dividendos acumulados
    dividends_acc = player.dividendHolding if player.dividendHolding is not None else 0

    initial_endowment = player.initialCash + player.assetValue * player.initialAssets
    end_endowment = player.cashHolding + player.assetValue * player.assetsHolding + dividends_acc
    player.tradingProfit = end_endowment - initial_endowment

    # Guardamos el resultado en el jugador
    player.tradingProfit = round(player.tradingProfit, C.decimals)

    # Cambio porcentual en la riqueza
    
    if not player.isObserver and player.isParticipating and initial_endowment != 0:
        player.wealthChange = (end_endowment - initial_endowment) / initial_endowment
    else:
       player.wealthChange = 0
    player.payoff = max(C.base_payment + C.multiplier * player.wealthChange, C.min_payment_in_round)

    #print(f"[CALC PROFIT] Jugador {player.id_in_group} - Ronda {group.round_number}")
    #print(f"  - Inicial: Cash={player.initialCash}, Activos={player.initialAssets}, Valor Activos={player.assetValue}")
    #print(f"  - Final: Cash={player.cashHolding}, Activos={player.assetsHolding}, Valor Final de activos={end_endowment}, Dividendos={dividends_acc}")
    #print(f"  - Ganancia: {player.tradingProfit}, Cambio Riqueza: {player.wealthChange}%")



def calc_final_profit(player: Player):
    """ Calcula el pago final del jugador basado en una ronda aleatoria. """

    # Filtrar rondas después de los trial rounds
    period_payoffs = [p.payoff for p in player.in_all_rounds() if p.round_number > C.num_trial_rounds]

    if period_payoffs:
        # Seleccionar una ronda aleatoria entre las jugadas
        selected_index = np.random.choice(len(period_payoffs))  
        player.selectedRound = selected_index + C.num_trial_rounds + 1  # Ajustar índice al número de ronda
        player.finalPayoff = max(period_payoffs[selected_index], C.min_payment)  # Aplicar mínimo pago

        print(f"[FINAL PROFIT] Jugador {player.id_in_group} - Ronda Seleccionada: {player.selectedRound}")
        print(f"  - Pago de la ronda seleccionada: {period_payoffs[selected_index]}")
        print(f"  - Pago final aplicado: {player.finalPayoff}")
    else:
        # Si no hay rondas jugadas, asignar el mínimo pago
        player.selectedRound = C.num_trial_rounds + 1  
        player.finalPayoff = C.min_payment

        print(f"[FINAL PROFIT] Jugador {player.id_in_group} - No hay rondas válidas. Pago mínimo aplicado: {player.finalPayoff}")



def custom_export(players):
    # this function defines the variables that are downloaded in customised tables
    # Export Limits
    yield ['TableName', 'sessionID', 'offerID', 'group', 'Period', 'maker', 'price', 'limitVolume', 'isBid', 'offerID', 'orderID', 'offerTime', 'remainingVolume', 'isActive', 'bestAskBefore', 'bestBidBefore', 'bestAskAfter', 'bestBidAfter']
    limits = Limit.filter()
    for l in limits:
        yield ['Limits', l.group.session.code, l.offerID, l.group.id_in_subsession, l.group.round_number, l.makerID, l.price, l.limitVolume, l.isBid, l.orderID, l.offerTime, l.remainingVolume, l.isActive, l.bestAskBefore, l.bestBidBefore, l.bestAskAfter, l.bestBidAfter]

    # Export Transactions
    yield ['TableName', 'sessionID', 'transactionID', 'group', 'Period', 'maker', 'taker', 'price', 'transactionVolume', 'limitVolume', 'sellerID', 'buyerID', 'isBid', 'offerID', 'orderID', 'offerTime', 'transactionTime', 'remainingVolume', 'isActive', 'bestAskBefore', 'bestBidBefore', 'bestAskAfter', 'bestBidAfter']
    trades = Transaction.filter()
    for t in trades:
        yield ['Transactions', t.group.session.code, t.transactionID, t.group.id_in_subsession, t.group.round_number, t.makerID, t.takerID, t.price, t.transactionVolume, t.limitVolume, t.sellerID, t.buyerID, t.isBid, t.offerID, t.orderID, t.offerTime, t.transactionTime, t.remainingVolume, t.isActive, t.bestAskBefore, t.bestBidBefore, t.bestAskAfter, t.bestBidAfter]

    # Export Orders
    yield ['TableName', 'sessionID', 'orderID', 'orderType', 'group', 'Period', 'maker', 'taker', 'price', 'transactionVolume', 'limitVolume', 'sellerID', 'buyerID', 'isBid', 'offerID', 'transactionID', 'offerTime', 'transactionTime', 'remainingVolume', 'isActive', 'bestAskBefore', 'bestBidBefore', 'bestAskAfter', 'bestBidAfter']
    orders = Order.filter()
    for o in orders:
        yield ['Orders', o.group.session.code, o.orderID, o.orderType, o.group.id_in_subsession, o.group.round_number, o.makerID, o.takerID, o.price, o.transactionVolume, o.limitVolume, o.sellerID, o.buyerID, o.isBid, o.offerID, o.transactionID, o.offerTime, o.transactionTime, o.remainingVolume, o.isActive, o.bestAskBefore, o.bestBidBefore, o.bestAskAfter, o.bestBidAfter]

    # Export BidAsk
    yield ['TableName', 'sessionID', 'orderID', 'operationType', 'group', 'Period', 'bestAsk', 'bestBid', 'BATime', 'timing']
    bidasks = BidAsks.filter()
    for b in bidasks:
        yield ['BidAsks', b.group.session.code, b.orderID, b.operationType, b.group.id_in_subsession, b.group.round_number, b.bestAsk, b.bestBid, b.BATime, b.timing]

    # Export News
    yield ['TableName', 'sessionID', 'message', 'group', 'Period', 'playerID', 'msgTime']
    news = News.filter()
    for n in news:
        yield ['BidAsks', n.group.session.code, n.msg, n.group.id_in_subsession, n.group.round_number, n.playerID, n.msgTime]

def custom_export(players):
    # Exportar dividendos por jugador y ronda
    yield ['TableName', 'sessionID', 'playerID', 'group', 'Period', 'initialDividend', 'dividendHolding', 'dividendByAsset']
    for p in players:
        yield ['Dividends', p.group.session.code, p.id_in_group, p.group.id_in_subsession, p.round_number, p.initialDividend, p.dividendHolding, p.dividendByAsset]


class Limit(ExtraModel):
    offerID = models.IntegerField()
    orderID = models.IntegerField()
    makerID = models.IntegerField()
    group = models.Link(Group)
    Period = models.IntegerField()
    maker = models.Link(Player)
    limitVolume = models.IntegerField()
    price = models.FloatField(decimal=C.decimals)
    transactedVolume = models.IntegerField()
    remainingVolume = models.IntegerField()
    amount = models.FloatField(decimal=C.decimals)
    isBid = models.BooleanField(choices=((True, 'Bid'), (False, 'Ask')))
    offerTime = models.FloatField(doc="Timestamp (seconds since beginning of trading)")
    isActive = models.BooleanField(choices=((True, 'active'), (False, 'inactive')))
    bestBidBefore = models.FloatField()
    bestAskBefore = models.FloatField()
    bestAskAfter = models.FloatField()
    bestBidAfter = models.FloatField()


def limit_order(player: Player, data):
    # this code is run at the market page, within the live_method(), whenever a participants aimes to create a limit order.
    # this function processes limit orders and creates new entries in the Limit and Order tables.
    maker_id = player.id_in_group
    group = player.group
    period = group.round_number
    if player.isObserver:
        News.create(
            player=player,
            playerID=maker_id,
            group=group,
            Period=period,
            msg='Orden rechazada: eres un observador y no puedes colocar una orden límite.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    if not (data['isBid'] >= 0 and data['limitPrice'] and data['limitVolume']):
        News.create(
            player=player,
            playerID=maker_id,
            group=group,
            Period=period,
            msg='Orden rechazada: precio, volumen o activo mal especificado.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    price = round(float(data['limitPrice']), C.decimals)
    is_bid = bool(data['isBid'] == 1)
    limit_volume = int(data['limitVolume'])
    if not (price > 0 and limit_volume > 0):
        News.create(
            player=player,
            playerID=maker_id,
            group=group,
            Period=period,
            msg='Orden rechazada: precio o volumen mal especificado.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    if is_bid and player.cashHolding + player.capLong - player.cashOffered - limit_volume * price < 0:
        News.create(
            player=player,
            playerID=maker_id,
            group=group,
            Period=period,
            msg='Orden rechazada: saldo insuficiente disponible.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    best_ask_before = group.field_maybe_none('bestAsk')
    best_bid_before = group.field_maybe_none('bestBid')
    if not is_bid and player.assetsHolding + player.capShort - player.assetsOffered - limit_volume < 0:
        News.create(
            player=player,
            playerID=maker_id,
            group=group,
            Period=period,
            msg='Orden rechazada: activos insuficientes disponibles.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    elif (is_bid and best_ask_before is not None and price > best_ask_before) or (not is_bid and best_bid_before is not None and price < best_bid_before):
        News.create(
            player=player,
            playerID=maker_id,
            group=group,
            Period=period,
            msg='Orden rechazada: hay una orden límite con el mismo precio o un precio más favorable disponible en el libro de órdenes',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    offer_id = player.subsession.offerID + 1
    player.subsession.offerID += 1
    while len(Limit.filter(group=group, offerID=offer_id)) > 0:  # to prevent duplicates in offerID
        offer_id += 1
    offer_time = round(float(time.time() - player.group.marketStartTime), C.decimals)
    order_id = player.subsession.orderID + 1
    player.subsession.orderID += 1
    while len(Order.filter(group=group, offerID=order_id)) > 0:  # to prevent duplicates in orderID
        order_id += 1
    if best_ask_before:
        best_ask_after = best_ask_before
    else:
        best_ask_before = -1
        best_ask_after = -1
    if best_bid_before:
        best_bid_after = best_bid_before
    else:
        best_bid_before = -1
        best_bid_after = -1
    if is_bid and (best_bid_before == -1 or price >= best_bid_before):
        best_bid_after = price
    elif not is_bid and (best_ask_before == -1 or price <= best_ask_before):
        best_ask_after = price
    Limit.create(
        offerID=offer_id,
        orderID=order_id,
        makerID=maker_id,
        group=group,
        Period=period,
        limitVolume=limit_volume,
        price=price,
        transactedVolume=0,
        remainingVolume=limit_volume,
        amount=limit_volume * price,
        isBid=is_bid,
        offerTime=offer_time,
        isActive=True,
        bestAskBefore=best_ask_before,
        bestBidBefore=best_bid_before,
        bestAskAfter=best_ask_after,
        bestBidAfter=best_bid_after,
    )
    Order.create(
        orderID=order_id,
        offerID=offer_id,
        makerID=maker_id,
        group=group,
        Period=period,
        limitVolume=limit_volume,
        price=price,
        transactedVolume=0,
        remainingVolume=limit_volume,
        amount=limit_volume * price,
        isBid=is_bid,
        orderType='limitOrder',
        offerTime=offer_time,
        orderTime=offer_time,
        isActive=True,
        bestAskBefore=best_ask_before,
        bestBidBefore=best_bid_before,
        bestAskAfter=best_ask_after,
        bestBidAfter=best_bid_after,
    )
    player.limitOrders += 1
    player.limitVolume += limit_volume
    group.limitOrders += 1
    group.limitVolume += limit_volume
    if is_bid:
        player.cashOffered += limit_volume * price
        player.limitBuyOrders += 1
        player.limitBuyVolume += limit_volume
        group.limitBuyOrders += 1
        group.limitBuyVolume += limit_volume
    else:
        player.assetsOffered += limit_volume
        player.limitSellOrders += 1
        player.limitSellVolume += limit_volume
        group.limitSellOrders += 1
        group.limitSellVolume += limit_volume


def cancel_limit(player: Player, data):
    # this code is run at the market page, within the live_method(), whenever a participants aimes to create a limit order.
    # this function processes limit order withdrawals and creates new entries in the Order table.
    if 'offerID' not in data:
        return
    maker_id = int(data['makerID'])
    group = player.group
    period = group.round_number
    if player.isObserver:
        News.create(
            player=player,
            playerID=maker_id,
            group=group,
            Period=period,
            msg='Order rejected: you are an observer who cannot withdraw a limit order.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    if maker_id != player.id_in_group:
        News.create(
            player=player,
            playerID=maker_id,
            group=group,
            Period=period,
            msg='Order rejected: you can withdraw your own orders only.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    offer_id = int(data['offerID'])
    # we need to update Limit table entry
    offers = [o for o in Limit.filter(group=group) if o.offerID == offer_id]
    if not offers or len(offers) != 1:
        print('Error: too few or too many limits found while withdrawing.')
        return
    offers[0].isActive = False
    is_bid = offers[0].isBid
    limit_volume = offers[0].limitVolume
    remaining_volume = offers[0].remainingVolume
    price = offers[0].price
    transacted_volume = offers[0].transactedVolume
    offer_time = offers[0].offerTime
    if price != float(data['limitPrice']) or is_bid != bool(data['isBid'] == 1):
        print('Odd request when player', maker_id, 'cancelled an order', data)
    order_id = player.subsession.orderID + 1
    player.subsession.orderID += 1
    while len(Order.filter(group=group, offerID=order_id)) > 0:  # to prevent duplicates in orderID
        order_id += 1
    best_ask_before = group.field_maybe_none('bestAsk')
    best_bid_before = group.field_maybe_none('bestBid')
    limitoffers = Limit.filter(group=group)
    best_bid_after = max([offer.price for offer in limitoffers if offer.isActive and offer.isBid] or [-1])
    best_ask_after = min([offer.price for offer in limitoffers if offer.isActive and not offer.isBid] or [-1])
    if not best_ask_before:
        best_ask_before = -1
    if not best_bid_before:
        best_bid_before = -1
    Order.create(
        orderID=order_id,
        offerID=offer_id,
        makerID=maker_id,
        group=group,
        Period=period,
        limitVolume=limit_volume,
        price=price,
        transactedVolume=transacted_volume,
        remainingVolume=0,
        amount=limit_volume * price,
        isBid=is_bid,
        orderType='cancelLimitOrder',
        offerTime=offer_time,
        orderTime=float(time.time() - player.group.marketStartTime),
        isActive=False,
        bestAskBefore=best_ask_before,
        bestBidBefore=best_bid_before,
        bestAskAfter=best_ask_after,
        bestBidAfter=best_bid_after,
    )
    player.cancellations += 1
    player.cancelledVolume += remaining_volume
    group.cancellations += 1
    group.cancelledVolume += remaining_volume
    if is_bid:
        player.cashOffered -= remaining_volume * price
    else:
        player.assetsOffered -= remaining_volume


class Order(ExtraModel):
    orderID = models.IntegerField()
    offerID = models.IntegerField()
    transactionID = models.IntegerField()
    makerID = models.IntegerField()
    takerID = models.IntegerField()
    sellerID = models.IntegerField()
    buyerID = models.IntegerField()
    group = models.Link(Group)
    Period = models.IntegerField()
    limitVolume = models.IntegerField()
    transactionVolume = models.IntegerField()
    transactedVolume = models.IntegerField()
    remainingVolume = models.IntegerField()
    price = models.FloatField(decimal=C.decimals)
    amount = models.FloatField(decimal=C.decimals)
    isBid = models.BooleanField(choices=((True, 'Bid'), (False, 'Ask')))
    orderType = models.StringField()
    orderTime = models.FloatField(doc="Timestamp (seconds since beginning of trading)")
    offerTime = models.FloatField()
    transactionTime = models.FloatField()
    isActive = models.BooleanField(choices=((True, 'active'), (False, 'inactive')))
    bestBidBefore = models.FloatField()
    bestAskBefore = models.FloatField()
    bestAskAfter = models.FloatField()
    bestBidAfter = models.FloatField()


class Transaction(ExtraModel):
    transactionID = models.IntegerField()
    offerID = models.IntegerField()
    orderID = models.IntegerField()
    makerID = models.IntegerField()
    takerID = models.IntegerField()
    sellerID = models.IntegerField()
    buyerID = models.IntegerField()
    group = models.Link(Group)
    Period = models.IntegerField()
    transactionVolume = models.IntegerField()
    limitVolume = models.IntegerField()
    remainingVolume = models.IntegerField()
    price = models.FloatField(decimal=C.decimals)
    amount = models.FloatField(decimal=C.decimals)
    isBid = models.BooleanField(choices=((True, 'Bid'), (False, 'Ask')))
    offerTime = models.FloatField()
    transactionTime = models.FloatField(doc="Timestamp (seconds since beginning of trading)")
    isActive = models.BooleanField(choices=((True, 'active'), (False, 'inactive')))
    bestBidBefore = models.FloatField()
    bestAskBefore = models.FloatField()
    bestAskAfter = models.FloatField()
    bestBidAfter = models.FloatField()


def transaction(player: Player, data):
    # this code is run at the market page, within the live_method(), whenever a participants aimes to acccept a limit order, i.e., when a market order is made.
    # this function processes market orders and creates new entries in the Transaction and Order tables, and updates the Limit table.
    if 'offerID' not in data:
        return
    offer_id = int(data['offerID'])
    taker_id = player.id_in_group
    group = player.group
    period = group.round_number
    if player.isObserver:
        News.create(
            player=player,
            playerID=taker_id,
            group=group,
            Period=period,
            msg='Order rejected: you are an observer who cannot accept a market order.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    limit_entry = Limit.filter(group=group, offerID=offer_id)
    if len(limit_entry) > 1:
        print('Limit entry is not well-defined: multiple entries with the same ID')
    limit_entry = limit_entry[0]
    transaction_volume = int(data['transactionVolume'])
    is_bid = limit_entry.isBid
    price = float(limit_entry.price)
    maker_id = int(limit_entry.makerID)
    remaining_volume = int(limit_entry.remainingVolume)
    limit_volume = int(limit_entry.limitVolume)
    if not (price > 0 and transaction_volume > 0): # check whether data is valid
        News.create(
            player=player,
            playerID=taker_id,
            group=group,
            Period=period,
            msg='Order rejected: misspecified volume.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    if price != float(data['transactionPrice']) or is_bid != bool(data['isBid'] == 1):
        print('Odd request when player', maker_id, 'accepted an order', data, 'while in the order book we find', limit_entry)
    is_active = limit_entry.isActive
    if transaction_volume >= remaining_volume:
        transaction_volume = remaining_volume
        is_active = False
    if not is_bid and player.cashHolding + player.capLong - player.cashOffered - transaction_volume * price < 0:
        News.create(
            player=player,
            playerID=taker_id,
            group=group,
            Period=period,
            msg='Order rejected: insufficient cash available.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    best_ask_before = group.field_maybe_none('bestAsk')
    best_bid_before = group.field_maybe_none('bestBid')
    if is_bid and player.assetsHolding + player.capShort - player.assetsOffered - transaction_volume < 0:
        News.create(
            player=player,
            playerID=taker_id,
            group=group,
            Period=period,
            msg='Order rejected: insufficient assets available.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    elif maker_id == taker_id:
        News.create(
            player=player,
            playerID=taker_id,
            group=group,
            Period=period,
            msg='Order rejected: own limit orders cannot be transacted.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    if (is_bid and best_bid_before and price < best_bid_before) or (not is_bid and best_ask_before and price > best_ask_before) :
        News.create(
            player=player,
            playerID=taker_id,
            group=group,
            Period=period,
            msg='Order rejected: there is a better offer available.',
            msgTime=round(float(time.time() - player.group.marketStartTime), C.decimals)
        )
        return
    offer_time = round(float(limit_entry.offerTime), C.decimals)
    players = group.get_players()
    maker = [p for p in players if p.id_in_group == maker_id][0]
    if is_bid:
        [buyer, seller] = [maker, player]
        maker.cashOffered -= transaction_volume * price
        maker.limitBuyOrderTransactions += 1
        maker.limitBuyVolumeTransacted += transaction_volume
        player.marketSellOrders += 1
        player.marketSellVolume += transaction_volume
        group.marketSellOrders += 1
        group.marketSellVolume += transaction_volume
        seller_id = player.id_in_group
        buyer_id = maker.id_in_group
    else:
        [buyer, seller] = [player, maker]
        maker.assetsOffered -= transaction_volume  # undo offer holdings
        maker.limitSellOrderTransactions += 1
        maker.limitSellVolumeTransacted += transaction_volume
        player.marketBuyOrders += 1
        player.marketBuyVolume += transaction_volume
        group.marketBuyOrders += 1
        group.marketBuyVolume += transaction_volume
        seller_id = maker.id_in_group
        buyer_id = seller.id_in_group
    transaction_id = player.subsession.transactionID + 1
    player.subsession.transactionID += 1
    while len(Transaction.filter(group=group, offerID=transaction_id)) > 0:  # to prevent duplicates in transactionID
        transaction_id += 1
    order_id = player.subsession.orderID + 1
    player.subsession.orderID += 1
    while len(Order.filter(group=group, offerID=order_id)) > 0:  # to prevent duplicates in orderID
        order_id += 1
    transaction_time = round(float(time.time() - group.marketStartTime), C.decimals)
    limit_entry.transactedVolume += transaction_volume
    limit_entry.isActive = is_active
    transacted_volume = limit_entry.transactedVolume
    limit_entry.remainingVolume -= transaction_volume
    buyer.cashHolding -= transaction_volume * price
    seller.cashHolding += transaction_volume * price
    buyer.transactions += 1
    buyer.transactedVolume += transaction_volume
    buyer.assetsHolding += transaction_volume
    seller.transactions += 1
    seller.transactedVolume += transaction_volume
    seller.assetsHolding -= transaction_volume
    print(f"[TRADE] Jugador {seller.id_in_group} vendió {transaction_volume} activos. Tenencia actual: {seller.assetsHolding}")

    maker.limitOrderTransactions += 1
    maker.limitVolumeTransacted += transaction_volume
    # Transferir dividendHolding proporcionalmente a los activos vendidos
    #buyer.dividendHolding += (seller.dividendHolding / seller.assetsHolding) * transaction_volume if seller.assetsHolding > 0 else 0
    #seller.dividendHolding -= (seller.dividendHolding / seller.assetsHolding) * transaction_volume if seller.assetsHolding > 0 else 0

    player.marketOrders += 1
    player.marketOrderVolume += transaction_volume
    group.transactions += 1
    group.transactedVolume += transaction_volume
    limitOffers = Limit.filter(group=group)
    best_bid_after = max([offer.price for offer in limitOffers if offer.isActive and offer.isBid] or [-1])
    best_ask_after = min([offer.price for offer in limitOffers if offer.isActive and not offer.isBid] or [-1])
    if not best_ask_before:
        best_ask_before = -1
    if not best_bid_before:
        best_bid_before = -1
    Transaction.create(
        transactionID=transaction_id,
        offerID=offer_id,
        orderID=order_id,
        makerID=maker_id,
        takerID=taker_id,
        sellerID=seller_id,
        buyerID=buyer_id,
        group=group,
        Period=period,
        price=price,
        transactionVolume=transaction_volume,
        remainingVolume=remaining_volume - transaction_volume,
        amount=transaction_volume * price,
        isBid=is_bid,
        transactionTime=transaction_time,
        offerTime=offer_time,
        isActive=is_active,
        bestAskBefore=best_ask_before,
        bestBidBefore=best_bid_before,
        bestAskAfter=best_ask_after,
        bestBidAfter=best_bid_after,
    )
    Order.create(
        orderID=order_id,
        offerID=offer_id,
        transactionID=transaction_id,
        group=group,
        Period=period,
        makerID=maker_id,
        takerID=taker_id,
        sellerID=seller_id,
        buyerID=buyer_id,
        limitVolume=limit_volume,
        price=price,
        transactedVolume=transacted_volume,
        remainingVolume=remaining_volume - transaction_volume,
        amount=limit_volume * price,
        isBid=is_bid,
        orderType='marketOrder',
        orderTime=transaction_time,
        offerTime=offer_time,
        isActive=is_active,
        bestAskBefore=best_ask_before,
        bestBidBefore=best_bid_before,
        bestAskAfter=best_ask_after,
        bestBidAfter=best_bid_after,
    )
def store_group_transactions(group: Group):
    """
    Extrae las transacciones desde `Transaction` y las almacena en `GroupTransactions`
    para hacerlas accesibles a todos los jugadores del grupo.
    """
    # 🔥 Obtener todas las transacciones de la ronda actual
    new_transactions = Transaction.filter(group=group, Period=group.round_number)

    #print(f"\n📊 [CHECK TRANSACTION] Transacciones en `Transaction` antes de guardar en `GroupTransactions`:")
    #if not new_transactions:
    #    print("  ⚠️ No hay transacciones nuevas para almacenar.")

    #for tx in new_transactions:
    #    print(f"  - Ronda {tx.Period}, ID: {tx.transactionID}, Precio: {tx.price}, "
    #          f"Volumen: {tx.transactionVolume}, Vendedor: {tx.sellerID}, Comprador: {tx.buyerID}, Tiempo: {tx.transactionTime}")

    # 🔍 Obtener IDs de transacciones ya almacenadas en `GroupTransactions`
    existing_tx_ids = {tx.transactionID for tx in GroupTransactions.filter(group=group)}

 # 📌 Recuperar transacciones previas almacenadas en session.vars
    session_transactions = group.session.vars.get('session_transactions', [])

    # 🔄 Guardar solo transacciones nuevas en `GroupTransactions` y `session.vars`
    for tx in new_transactions:
        if tx.transactionID not in existing_tx_ids:
            # ✅ Guardar en `GroupTransactions`
            GroupTransactions.create(
                group=group,
                round_number=tx.Period,
                transactionID=tx.transactionID,
                price=tx.price,
                volume=tx.transactionVolume,
                sellerID=tx.sellerID,
                buyerID=tx.buyerID,
                time=tx.transactionTime
            )

            # ✅ Agregar a `session.vars` sin sobrescribir datos previos
            session_transactions.append({
                "round_number": tx.Period,
                "transactionID": tx.transactionID,
                "price": tx.price,
                "volume": tx.transactionVolume,
                "sellerID": tx.sellerID,
                "buyerID": tx.buyerID,
                "time": tx.transactionTime
            })

    # 🛠️ Actualizar `session.vars` con todas las transacciones acumuladas
    group.session.vars['session_transactions'] = session_transactions

   # print(f"\n✅ [STORE TRANSACTIONS] Transacciones almacenadas en `session.vars` hasta la Ronda {group.round_number}:")
   # for tx in session_transactions:
    #    print(f"  - Ronda {tx['round_number']}, ID: {tx['transactionID']}, Precio: {tx['price']}, "
    #          f"Volumen: {tx['volume']}, Vendedor: {tx['sellerID']}, Comprador: {tx['buyerID']}, Tiempo: {tx['time']}")
        
def get_session_transactions(group: Group):
    """
    Recupera todas las transacciones almacenadas en `session.vars`.
    """
    session_transactions = group.session.vars.get('session_transactions', [])

   # print(f"\n📊 [CHECK SESSION TRANSACTIONS] Transacciones acumuladas en toda la sesión:")
    #if not session_transactions:
    #    print("  ⚠️ No hay transacciones en session.vars.")
    #else:
     #   for tx in session_transactions:
      #      print(f"  - Ronda {tx['round_number']}, ID: {tx['transactionID']}, Precio: {tx['price']}, "
       #           f"Volumen: {tx['volume']}, Vendedor: {tx['sellerID']}, Comprador: {tx['buyerID']}, Tiempo: {tx['time']}")

    return session_transactions



class GroupTransactions(ExtraModel):
    session = models.Link(Subsession)
    round_number = models.IntegerField()
    volume = models.IntegerField()
    time = models.FloatField()
    transactionID = models.IntegerField()
    offerID = models.IntegerField()
    orderID = models.IntegerField()
    makerID = models.IntegerField()
    takerID = models.IntegerField()
    sellerID = models.IntegerField()
    buyerID = models.IntegerField()
    group = models.Link(Group)
    Period = models.IntegerField()
    transactionVolume = models.IntegerField()
    limitVolume = models.IntegerField()
    remainingVolume = models.IntegerField()
    price = models.FloatField(decimal=C.decimals)
    amount = models.FloatField(decimal=C.decimals)
    isBid = models.BooleanField(choices=((True, 'Bid'), (False, 'Ask')))
    offerTime = models.FloatField()
    transactionTime = models.FloatField(doc="Timestamp (seconds since beginning of trading)")
    isActive = models.BooleanField(choices=((True, 'active'), (False, 'inactive')))
    bestBidBefore = models.FloatField()
    bestAskBefore = models.FloatField()
    bestAskAfter = models.FloatField()
    bestBidAfter = models.FloatField()


class News(ExtraModel):
    player = models.Link(Player)
    playerID = models.IntegerField()
    group = models.Link(Group)
    Period = models.IntegerField()
    msg = models.StringField()
    msgTime = models.FloatField()


class BidAsks(ExtraModel):
    group = models.Link(Group)
    Period = models.IntegerField()
    assetValue = models.StringField()
    orderID = models.IntegerField()
    bestBid = models.FloatField()
    bestAsk = models.FloatField()
    BATime = models.FloatField()
    timing = models.StringField()
    operationType = models.StringField()


# PAGES
class Instructions(Page):
    form_model = 'player'
    form_fields = ['isParticipating']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            numTrials=C.num_trial_rounds,
            numRounds=C.NUM_ROUNDS - C.num_trial_rounds,
        )


class WaitToStart(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        group.randomisedTypes = random_types(group=group)
        initiate_group(group=group)
        players = group.get_players()
        for p in players:
            p.assetValue = group.assetValue
            if p.isParticipating:
                set_player(player=p)
                initiate_player(player=p)
                store_player_financials(p)  # Guarda valores iniciales
                print(f"\n[WAIT TO START] Jugador {p.id_in_group} - Ronda {group.round_number}")

class EndOfTrialRounds(Page):
    template_name = "_templates/endOfTrialRounds.html"

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.num_trial_rounds + 1 and C.num_trial_rounds > 0 and player.isParticipating == 1
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        group = player.group  # ✅ Obtener el grupo del jugador

        # 🔥 Llamar a `store_group_transactions` para reiniciar las transacciones
        store_group_transactions(group)  # ✅ Esto almacena transacciones antes de resetear

        # 🔄 Reiniciar el almacenamiento de transacciones en session.vars
        group.session.vars['session_transactions'] = []  # ✅ Esto borra las transacciones acumuladas
        # SESSION TRANSACTIONS] Se han limpiado las transacciones acumuladas al final de la fase de prueba.")

class PreMarket(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.isParticipating == 1

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            round=player.round_number - C.num_trial_rounds,
            possible_dividends=", ".join(map(str, C.dividend_values))  # 🔹 Convertimos la lista a string aquí

        )

    @staticmethod
    def js_vars(player: Player):
        print(f"[PRE MARKET] Jugador {player.id_in_group} - Ronda {player.round_number}")
        print(f"  - Dividendos acumulados: {player.dividendHolding}")
        print(f"  - Efectivo disponible: {player.cashHolding}")
        print(f"  - Activos en tenencia: {player.assetsHolding}")

        return dict(
            allowShort=player.allowShort,
            capShort=player.capShort,
            capLong=player.capLong,
            cashHolding=round(player.cashHolding, C.decimals),
            dividendHolding=round(player.dividendHolding, C.decimals),  # Aquí se está enviando solo el nuevo dividendo
        )
    



class WaitingMarket(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        group.marketStartTime = round(float(time.time()), C.decimals)
        group.marketTime = get_max_time(group=group)


class Market(Page):
    live_method = live_method
    timeout_seconds = Group.marketTime

    @staticmethod
    def is_displayed(player: Player):
        return player.isParticipating

    @staticmethod
    def js_vars(player: Player):
        group = player.group
        session_transactions = get_session_transactions(group)
        transactions_list = [
            {
                "transactionID": tx["transactionID"],
                "price": tx["price"],
                "volume": tx["volume"],
                "round": tx["round_number"],
                "buyer": tx["buyerID"],
                "seller": tx["sellerID"],
                "time": tx["time"],
            }
            for tx in session_transactions
        ]

        #print(f"\n📊 [DEBUG JS_VARS] Enviando TODAS las transacciones de sesión al frontend:")
        #for tx in transactions_list:
        #    print(f"  - Ronda {tx['round']}, ID: {tx['transactionID']}, Precio: {tx['price']}, "
        #        f"Volumen: {tx['volume']}, Vendedor: {tx['seller']}, Comprador: {tx['buyer']}, Tiempo: {tx['time']}")

        print(f"[DEBUG] MARKET Tiempo de mercado en Ronda {group.round_number}: {group.marketTime}")
        return dict(
            id_in_group=player.id_in_group,
            transactions=transactions_list,
            allowShort=player.allowShort,
            capShort=player.capShort,
            capLong=player.capLong,  # round(player.capLong, 2)
            cashHolding=player.cashHolding,
            assetsHolding=player.assetsHolding,
            marketTime=group.marketTime,
            dividendHolding=player.dividendHolding,
        )

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            possible_dividends=", ".join(map(str, C.dividend_values))  # 🔹 Convertimos la lista a string aquí

        )
    @staticmethod
    def get_timeout_seconds(player: Player):
        group = player.group
        if player.isParticipating == 0:
            return 1
        else:
            return group.marketStartTime + group.marketTime - time.time()


class ResultsWaitPage(WaitPage):
    @staticmethod
    def is_displayed(player: Player):
        return player.isParticipating == 1

    @staticmethod
    def after_all_players_arrive(group: Group):
        players = group.get_players()
        for p in players:
            calc_round_profit(p)  # Calcula la ganancia de cada jugador      
        # Solo calcular el pago final si es la última ronda
        if group.round_number == C.NUM_ROUNDS:
            for p in players:
                calc_final_profit(player=p)
                #print(f"[FINAL PROFIT] Jugador {p.id_in_group}: Pago final = {p.finalPayoff}")



class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.isParticipating == 1

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            assetValue=round(player.assetValue, C.decimals),
            assetsHolding=round(player.assetsHolding, C.decimals),
            initialCash=round(player.initialCash, C.decimals),
            cashHolding=round(player.cashHolding, C.decimals),
            tradingProfit=round(player.tradingProfit, C.decimals),
            wealthChange=round(player.wealthChange, C.decimals),
            payoff=cu(round(player.payoff, C.decimals)),
            dividendGet=round(player.initialDividend, C.decimals),
            dividendsInRound=round(player.dividendByAsset, C.decimals),

        )

    @staticmethod
    def js_vars(player: Player):
        return dict(
            assetValue=round(player.assetValue, C.decimals),
        )


class FinalResults(Page):
    template_name = "_templates/finalResults.html"

    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS and player.isParticipating == 1

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            payoff=cu(round(player.finalPayoff, 0)),
            periodPayoff=[[p.round_number - C.num_trial_rounds, round(p.payoff, C.decimals), round(p.tradingProfit, C.decimals), round(p.wealthChange * 100, C.decimals)] for p in player.in_all_rounds() if p.round_number > C.num_trial_rounds],
        )


page_sequence = [Instructions, WaitToStart, EndOfTrialRounds, PreMarket, WaitingMarket, Market, ResultsWaitPage, Results, FinalResults, ResultsWaitPage]
