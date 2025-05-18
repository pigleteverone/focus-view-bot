import random
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from models import User, GameHistory

games_bp = Blueprint('games', __name__, url_prefix='/games')

@games_bp.route('/coinflip', methods=['GET', 'POST'])
@login_required
def coinflip():
    if request.method == 'POST':
        bet_amount = request.form.get('bet_amount', type=int)
        choice = request.form.get('choice')
        
        # Validate inputs
        if not bet_amount or bet_amount <= 0:
            flash('Please enter a valid bet amount', 'danger')
            return redirect(url_for('games.coinflip'))
            
        if choice not in ['heads', 'tails']:
            flash('Please choose either heads or tails', 'danger')
            return redirect(url_for('games.coinflip'))
            
        # Check if user has enough money
        if bet_amount > current_user.cash:
            flash('You don\'t have enough coins for this bet', 'danger')
            return redirect(url_for('games.coinflip'))
            
        # Flip the coin
        result = random.choice(['heads', 'tails'])
        
        # Determine outcome
        if result == choice:
            # Win (2x bet)
            winnings = bet_amount
            outcome = 'win'
            current_user.cash += winnings
            flash(f'The coin landed on {result}! You won {winnings} coins!', 'success')
        else:
            # Loss
            winnings = -bet_amount
            outcome = 'loss'
            current_user.cash -= bet_amount
            flash(f'The coin landed on {result}. You lost {bet_amount} coins.', 'danger')
        
        # Record the game
        GameHistory.record_game(
            user_id=current_user.id,
            game_type='coinflip',
            bet_amount=bet_amount,
            outcome=outcome,
            winnings=winnings
        )
        
        # Add XP if user won
        if outcome == 'win':
            current_user.add_xp(100)
            
        db.session.commit()
        
        return redirect(url_for('games.coinflip'))
    
    return render_template('games/coinflip.html')

@games_bp.route('/blackjack', methods=['GET', 'POST'])
@login_required
def blackjack():
    if request.method == 'POST':
        bet_amount = request.form.get('bet_amount', type=int)
        
        # Validate inputs
        if not bet_amount or bet_amount <= 0:
            flash('Please enter a valid bet amount', 'danger')
            return redirect(url_for('games.blackjack'))
            
        # Check if user has enough money
        if bet_amount > current_user.cash:
            flash('You don\'t have enough coins for this bet', 'danger')
            return redirect(url_for('games.blackjack'))
        
        # Initialize the blackjack game state in session
        return render_template('games/blackjack.html', bet_amount=bet_amount)
    
    return render_template('games/blackjack.html')

@games_bp.route('/blackjack/play', methods=['POST'])
@login_required
def blackjack_play():
    data = request.json
    action = data.get('action')
    bet_amount = data.get('bet_amount', 0)
    player_hand = data.get('player_hand', [])
    dealer_hand = data.get('dealer_hand', [])
    game_state = data.get('game_state', 'betting')
    
    bet_amount = int(bet_amount)
    
    # Initial deal
    if game_state == 'betting':
        # Create a deck and shuffle
        suits = ['hearts', 'diamonds', 'clubs', 'spades']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [{'value': v, 'suit': s} for v in values for s in suits]
        random.shuffle(deck)
        
        # Deal initial cards
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        
        return jsonify({
            'player_hand': player_hand,
            'dealer_hand': dealer_hand,
            'game_state': 'player_turn',
            'message': 'Your turn. Hit or Stand?',
            'deck': deck
        })
    
    # Player's turn actions
    if game_state == 'player_turn':
        deck = data.get('deck', [])
        
        if action == 'hit':
            # Deal another card to player
            player_hand.append(deck.pop())
            
            # Check if player busted
            player_value = calculate_hand_value(player_hand)
            if player_value > 21:
                # Player busts, dealer wins
                process_game_outcome(current_user.id, 'blackjack', bet_amount, 'loss', -bet_amount)
                return jsonify({
                    'player_hand': player_hand,
                    'dealer_hand': dealer_hand,
                    'game_state': 'game_over',
                    'message': f'Bust! Your hand value is {player_value}. You lose {bet_amount} coins.',
                    'result': 'loss'
                })
            
            return jsonify({
                'player_hand': player_hand,
                'dealer_hand': dealer_hand,
                'game_state': 'player_turn',
                'message': f'Your hand value is {player_value}. Hit or Stand?',
                'deck': deck
            })
            
        elif action == 'stand':
            # Dealer's turn
            dealer_value = calculate_hand_value(dealer_hand)
            
            # Dealer draws until 17 or higher
            while dealer_value < 17 and len(deck) > 0:
                dealer_hand.append(deck.pop())
                dealer_value = calculate_hand_value(dealer_hand)
            
            # Determine winner
            player_value = calculate_hand_value(player_hand)
            
            result = ''
            message = ''
            winnings = 0
            
            if dealer_value > 21:
                # Dealer busts, player wins
                result = 'win'
                winnings = bet_amount
                message = f'Dealer busts with {dealer_value}! You win {bet_amount} coins!'
            elif dealer_value > player_value:
                # Dealer wins
                result = 'loss'
                winnings = -bet_amount
                message = f'Dealer wins with {dealer_value} vs your {player_value}. You lose {bet_amount} coins.'
            elif player_value > dealer_value:
                # Player wins
                result = 'win'
                winnings = bet_amount
                message = f'You win with {player_value} vs dealer\'s {dealer_value}! You win {bet_amount} coins!'
            else:
                # Push (tie)
                result = 'push'
                winnings = 0
                message = f'Push! Both you and the dealer have {player_value}. Your bet is returned.'
            
            process_game_outcome(current_user.id, 'blackjack', bet_amount, result, winnings)
            
            return jsonify({
                'player_hand': player_hand,
                'dealer_hand': dealer_hand,
                'game_state': 'game_over',
                'message': message,
                'result': result
            })
    
    return jsonify({'error': 'Invalid game state or action'})

def calculate_hand_value(hand):
    value = 0
    aces = 0
    
    for card in hand:
        if card['value'] in ['K', 'Q', 'J']:
            value += 10
        elif card['value'] == 'A':
            aces += 1
            value += 11
        else:
            value += int(card['value'])
    
    # Adjust for aces if needed
    while value > 21 and aces > 0:
        value -= 10
        aces -= 1
        
    return value

def process_game_outcome(user_id, game_type, bet_amount, outcome, winnings):
    user = User.query.get(user_id)
    
    if outcome == 'win':
        user.cash += winnings
        user.add_xp(100)
    elif outcome == 'loss':
        user.cash -= bet_amount
    # For push/tie, no cash changes
    
    GameHistory.record_game(
        user_id=user_id,
        game_type=game_type,
        bet_amount=bet_amount,
        outcome=outcome,
        winnings=winnings
    )
    
    db.session.commit()

@games_bp.route('/slots', methods=['GET', 'POST'])
@login_required
def slots():
    if request.method == 'POST':
        bet_amount = request.form.get('bet_amount', type=int)
        
        # Validate inputs
        if not bet_amount or bet_amount <= 0:
            flash('Please enter a valid bet amount', 'danger')
            return redirect(url_for('games.slots'))
            
        # Check if user has enough money
        if bet_amount > current_user.cash:
            flash('You don\'t have enough coins for this bet', 'danger')
            return redirect(url_for('games.slots'))
            
        # Generate slot results
        symbols = ['cherry', 'lemon', 'watermelon', 'melon', 'bell', 'diamond', 'heart', 'horseshoe', 'clover', 'moneybag', 'seven', 'bar'] 
        weights = [20, 15, 12, 10, 8, 7, 7, 5, 5, 3, 2, 1]  # Probability weights, rarer symbols have higher payouts
        
        # Get 3 random symbols based on weights
        results = random.choices(symbols, weights=weights, k=3)
        
        # Determine outcome
        winnings = -bet_amount  # Default: player loses bet
        outcome = 'loss'
        
        # Check for winning combinations
        if results[0] == results[1] == results[2]:
            # All three match - big win
            symbol_index = symbols.index(results[0])
            # Higher payouts for rarer symbols
            multipliers = {
                'cherry': 3,    # Common
                'lemon': 4,
                'watermelon': 6,
                'melon': 7,
                'bell': 8,
                'heart': 9,
                'diamond': 10,  
                'horseshoe': 12,
                'clover': 13,   # Lucky
                'moneybag': 14, # Money!
                'seven': 15,    # Rare
                'bar': 20       # Very rare
            }
            multiplier = multipliers.get(results[0], 5)  # Default to 5x if symbol not in dict
            winnings = bet_amount * multiplier
            outcome = 'win'
            # Add extra reward for special symbols
            if results[0] == 'seven':
                winnings += 100  # Bonus for triple sevens
            elif results[0] == 'bar':
                winnings += 200  # Bonus for triple bars
            elif results[0] == 'moneybag':
                winnings += 50   # Bonus for triple moneybags
            flash(f'JACKPOT! Three {results[0]} - You won {winnings} coins!', 'success')
        elif results[0] == results[1] or results[1] == results[2] or results[0] == results[2]:
            # Two match - small win
            winnings = bet_amount
            outcome = 'win'
            flash(f'Two matching symbols! You won {winnings} coins!', 'success')
        else:
            # No matches - loss
            current_user.cash -= bet_amount
            flash(f'No matches. You lost {bet_amount} coins.', 'danger')
        
        # Record the game
        GameHistory.record_game(
            user_id=current_user.id,
            game_type='slots',
            bet_amount=bet_amount,
            outcome=outcome,
            winnings=winnings
        )
        
        # Update user's cash and XP if they won
        if outcome == 'win':
            current_user.cash += winnings
            current_user.add_xp(100)
            
        db.session.commit()
        
        return render_template('games/slots.html', 
                              results=results,
                              bet_amount=bet_amount,
                              winnings=winnings,
                              outcome=outcome)
    
    return render_template('games/slots.html')
