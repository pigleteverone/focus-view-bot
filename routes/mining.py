from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from models import Mine, GameHistory

mining_bp = Blueprint('mining', __name__)

@mining_bp.route('/mine')
@login_required
def mine_info():
    """Show mine information and stats"""
    # Get user's mine or redirect to start if they don't have one
    user_mine = Mine.query.filter_by(user_id=current_user.id).first()
    
    if not user_mine:
        flash('You need to start a mine first!', 'warning')
        return redirect(url_for('mining.start_mine'))
        
    # Check if dig is available
    dig_available = True
    dig_cooldown = None
    
    if user_mine.last_dig:
        next_dig = user_mine.last_dig + timedelta(minutes=1)
        dig_available = datetime.utcnow() >= next_dig
        if not dig_available:
            dig_cooldown = next_dig - datetime.utcnow()
    
    # Get top miners for leaderboard
    top_miners = Mine.query.order_by(Mine.prestige_level.desc(), Mine.diamond.desc()).limit(5).all()
    
    return render_template('mining/mine.html', 
                          mine=user_mine,
                          dig_available=dig_available,
                          dig_cooldown=dig_cooldown,
                          top_miners=top_miners)

@mining_bp.route('/start_mine', methods=['GET', 'POST'])
@login_required
def start_mine():
    """Start a new mine or update mine name"""
    # Check if user already has a mine
    existing_mine = Mine.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        mine_name = request.form.get('mine_name')
        
        if not mine_name:
            mine_name = f"{current_user.username}'s Mine"
            
        if existing_mine:
            # Update existing mine name
            existing_mine.name = mine_name
            db.session.commit()
            flash(f'Your mine name has been updated to: {mine_name}!', 'success')
        else:
            # Create new mine
            new_mine = Mine()
            new_mine.user_id = current_user.id
            new_mine.name = mine_name
            db.session.add(new_mine)
            db.session.commit()
            flash(f'Congratulations! You\'ve started a new mine: {mine_name}!', 'success')
            
            # Grant XP for starting a mine
            current_user.add_xp(50)
            
        return redirect(url_for('mining.mine_info'))
    
    return render_template('mining/start_mine.html', existing_mine=existing_mine)

@mining_bp.route('/dig')
@login_required
def dig():
    """Dig in the mine to find resources"""
    # Get user's mine
    user_mine = Mine.query.filter_by(user_id=current_user.id).first()
    
    if not user_mine:
        flash('You need to start a mine first!', 'warning')
        return redirect(url_for('mining.start_mine'))
    
    # Check cooldown
    if user_mine.last_dig:
        next_dig = user_mine.last_dig + timedelta(minutes=1)
        if datetime.utcnow() < next_dig:
            remaining = next_dig - datetime.utcnow()
            seconds = remaining.seconds
            flash(f'You need to wait {seconds} seconds before digging again!', 'warning')
            return redirect(url_for('mining.mine_info'))
    
    # Perform digging and get results
    results = user_mine.dig()
    
    # Add XP for digging
    current_user.add_xp(5)
    
    # Flash results
    flash_message = f'You dug and found: {results["coal"]} coal, {results["iron"]} iron, '
    flash_message += f'{results["gold"]} gold, and {results["unprocessed_material"]} unprocessed materials!'
    flash(flash_message, 'success')
    
    return redirect(url_for('mining.mine_info'))

@mining_bp.route('/process')
@login_required
def process():
    """Process unprocessed materials"""
    # Get user's mine
    user_mine = Mine.query.filter_by(user_id=current_user.id).first()
    
    if not user_mine:
        flash('You need to start a mine first!', 'warning')
        return redirect(url_for('mining.start_mine'))
    
    # Check if user has materials to process
    if user_mine.unprocessed_material <= 0:
        flash('You don\'t have any unprocessed materials to process!', 'warning')
        return redirect(url_for('mining.mine_info'))
    
    # Process materials and get results
    results = user_mine.process_materials()
    
    # Add XP for processing
    current_user.add_xp(10)
    
    # Flash results
    flash_message = f'You processed {user_mine.unprocessed_material} unprocessed materials and found: '
    flash_message += f'{results["diamond"]} diamond, {results["emerald"]} emerald, '
    flash_message += f'{results["lapis"]} lapis, and {results["redstone"]} redstone!'
    flash(flash_message, 'success')
    
    return redirect(url_for('mining.mine_info'))

@mining_bp.route('/inventory')
@login_required
def inventory():
    """Show mining inventory"""
    # Get user's mine
    user_mine = Mine.query.filter_by(user_id=current_user.id).first()
    
    if not user_mine:
        flash('You need to start a mine first!', 'warning')
        return redirect(url_for('mining.start_mine'))
    
    return render_template('mining/inventory.html', mine=user_mine)

@mining_bp.route('/craft', methods=['GET', 'POST'])
@login_required
def craft():
    """Craft packs from resources"""
    # Get user's mine
    user_mine = Mine.query.filter_by(user_id=current_user.id).first()
    
    if not user_mine:
        flash('You need to start a mine first!', 'warning')
        return redirect(url_for('mining.start_mine'))
    
    if request.method == 'POST':
        pack_type = request.form.get('pack_type')
        amount = int(request.form.get('amount', 1))
        
        # Validate amount
        if amount <= 0:
            flash('Amount must be at least 1', 'danger')
            return redirect(url_for('mining.craft'))
        
        # Map front-end names to backend names
        pack_mappings = {
            'tech': 'tech',
            'tp': 'tech',
            'tech_pack': 'tech',
            'utility': 'utility',
            'up': 'utility',
            'utility_pack': 'utility',
            'production': 'production',
            'pp': 'production',
            'production_pack': 'production'
        }
        
        # Get standardized pack type
        standardized_type = None
        if pack_type:
            standardized_type = pack_mappings.get(pack_type.lower())
        
        if not standardized_type:
            flash('Invalid pack type!', 'danger')
            return redirect(url_for('mining.craft'))
        
        # Attempt to craft
        result = user_mine.craft_pack(standardized_type, amount)
        
        if result['success']:
            # Add XP for crafting
            current_user.add_xp(15 * amount)
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'danger')
        
        return redirect(url_for('mining.inventory'))
    
    # Crafting requirements for reference
    crafting_requirements = {
        'tech': {
            'iron': 10,
            'gold': 5,
            'redstone': 2
        },
        'utility': {
            'iron': 15,
            'coal': 20,
            'lapis': 2
        },
        'production': {
            'iron': 20,
            'gold': 10,
            'diamond': 1
        }
    }
    
    return render_template('mining/craft.html', 
                          mine=user_mine, 
                          requirements=crafting_requirements)

@mining_bp.route('/mine/shop')
@login_required
def mine_shop():
    """Show the mining shop"""
    # Get user's mine
    user_mine = Mine.query.filter_by(user_id=current_user.id).first()
    
    if not user_mine:
        flash('You need to start a mine first!', 'warning')
        return redirect(url_for('mining.start_mine'))
    
    # Upgrade costs for reference
    upgrade_costs = {
        'digger': 500,
        'processor': 1000,
        'excavator': 2500,
        'drill': 5000,
        'dig_efficiency': 1500,
        'processing_efficiency': 2000
    }
    
    return render_template('mining/shop.html', 
                          mine=user_mine, 
                          upgrade_costs=upgrade_costs)

@mining_bp.route('/mine/upgrade', methods=['POST'])
@login_required
def upgrade_mine():
    """Buy upgrades for the mine"""
    # Get user's mine
    user_mine = Mine.query.filter_by(user_id=current_user.id).first()
    
    if not user_mine:
        flash('You need to start a mine first!', 'warning')
        return redirect(url_for('mining.start_mine'))
    
    upgrade_type = request.form.get('upgrade_type')
    amount = int(request.form.get('amount', 1))
    
    # Validate amount
    if amount <= 0:
        flash('Amount must be at least 1', 'danger')
        return redirect(url_for('mining.mine_shop'))
    
    # Attempt to purchase upgrade
    result = user_mine.buy_upgrade(upgrade_type, amount)
    
    if result['success']:
        # Add XP for upgrading
        current_user.add_xp(20 * amount)
        flash(result['message'], 'success')
        
        # Record transaction
        GameHistory.record_game(
            user_id=current_user.id,
            game_type='mine_upgrade',
            bet_amount=result['cost'],
            outcome='purchase',
            winnings=-result['cost']
        )
    else:
        flash(result['message'], 'danger')
    
    return redirect(url_for('mining.mine_shop'))