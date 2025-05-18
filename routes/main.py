from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from models import User, GameHistory, Leaderboard

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # Get top players for various leaderboards
    top_cash = User.query.order_by(User.cash.desc()).limit(5).all()
    top_level = User.query.order_by(User.level.desc()).limit(5).all()
    
    # Get recent games for display
    recent_games = GameHistory.query.order_by(GameHistory.played_at.desc()).limit(10).all()
    
    return render_template('index.html', 
                          top_cash=top_cash, 
                          top_level=top_level,
                          recent_games=recent_games)

@main_bp.route('/profile')
@login_required
def profile():
    # Get user's game history
    game_history = GameHistory.query.filter_by(user_id=current_user.id)\
                                 .order_by(GameHistory.played_at.desc())\
                                 .limit(20).all()
    
    # Get user's stats
    total_games = GameHistory.query.filter_by(user_id=current_user.id).count()
    wins = GameHistory.query.filter_by(user_id=current_user.id, outcome='win').count()
    losses = GameHistory.query.filter_by(user_id=current_user.id, outcome='loss').count()
    
    win_rate = (wins / total_games) * 100 if total_games > 0 else 0
    
    # Check cooldowns for all reward types
    daily_available = True
    work_available = True
    weekly_available = True
    monthly_available = True
    yearly_available = True
    overtime_available = True
    
    # Daily reward (resets at midnight)
    if current_user.last_daily:
        next_daily = current_user.last_daily.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        daily_available = datetime.utcnow() >= next_daily
    
    # Work reward (10 minute cooldown)
    if current_user.last_work:
        next_work = current_user.last_work + timedelta(minutes=10)
        work_available = datetime.utcnow() >= next_work
    
    # Weekly reward (7 days cooldown)
    if current_user.last_weekly:
        next_weekly = current_user.last_weekly + timedelta(days=7)
        weekly_available = datetime.utcnow() >= next_weekly
    
    # Monthly reward (30 days cooldown)
    if current_user.last_monthly:
        next_monthly = current_user.last_monthly + timedelta(days=30)
        monthly_available = datetime.utcnow() >= next_monthly
    
    # Yearly reward (365 days cooldown)
    if current_user.last_yearly:
        next_yearly = current_user.last_yearly + timedelta(days=365)
        yearly_available = datetime.utcnow() >= next_yearly
    
    # Overtime reward (3 hour cooldown)
    if current_user.last_overtime:
        next_overtime = current_user.last_overtime + timedelta(hours=3)
        overtime_available = datetime.utcnow() >= next_overtime
    
    return render_template('profile.html', 
                          game_history=game_history,
                          total_games=total_games,
                          wins=wins,
                          losses=losses,
                          win_rate=win_rate,
                          daily_available=daily_available,
                          work_available=work_available,
                          weekly_available=weekly_available,
                          monthly_available=monthly_available,
                          yearly_available=yearly_available,
                          overtime_available=overtime_available)

@main_bp.route('/leaderboard')
def leaderboard():
    # Get various leaderboards
    richest_users = User.query.order_by(User.cash.desc()).limit(20).all()
    highest_level = User.query.order_by(User.level.desc()).limit(20).all()
    
    # Most profitable game types
    game_profits = db.session.query(
        GameHistory.game_type,
        func.sum(GameHistory.winnings).label('total_profit')
    ).group_by(GameHistory.game_type).order_by(func.sum(GameHistory.winnings).desc()).all()
    
    return render_template('leaderboard.html',
                          richest_users=richest_users,
                          highest_level=highest_level,
                          game_profits=game_profits)

@main_bp.route('/help')
def help():
    return render_template('help.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/daily')
@login_required
def daily():
    # Check if user already claimed their daily reward
    if current_user.last_daily:
        next_daily = current_user.last_daily.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        if datetime.utcnow() < next_daily:
            flash('You already claimed your daily reward. Next reward available at midnight.', 'warning')
            return redirect(url_for('main.profile'))
    
    # Calculate reward based on level
    reward = 1000 + (current_user.level * 100)
    
    # Update user's cash and last_daily
    current_user.cash += reward
    current_user.last_daily = datetime.utcnow()
    
    # Record the transaction
    GameHistory.record_game(
        user_id=current_user.id,
        game_type='daily',
        bet_amount=0,
        outcome='reward',
        winnings=reward
    )
    
    db.session.commit()
    
    flash(f'You received {reward} coins as your daily reward!', 'success')
    return redirect(url_for('main.profile'))

@main_bp.route('/work')
@login_required
def work():
    # Check if cooldown has passed (10 minutes)
    if current_user.last_work:
        next_work = current_user.last_work + timedelta(minutes=10)
        if datetime.utcnow() < next_work:
            remaining = next_work - datetime.utcnow()
            minutes = remaining.seconds // 60
            seconds = remaining.seconds % 60
            flash(f'You need to wait {minutes}m {seconds}s before working again.', 'warning')
            return redirect(url_for('main.profile'))
    
    # Calculate reward based on level
    reward = 500 + (current_user.level * 50)
    
    # Update user's cash and last_work
    current_user.cash += reward
    current_user.last_work = datetime.utcnow()
    
    # Add XP for working
    current_user.add_xp(5)
    
    # Record the transaction
    GameHistory.record_game(
        user_id=current_user.id,
        game_type='work',
        bet_amount=0,
        outcome='reward',
        winnings=reward
    )
    
    db.session.commit()
    
    flash(f'You worked hard and earned {reward} coins and 5 XP!', 'success')
    return redirect(url_for('main.profile'))
    
@main_bp.route('/overtime')
@login_required
def overtime():
    # Check if cooldown has passed (3 hours)
    if current_user.last_overtime:
        next_overtime = current_user.last_overtime + timedelta(hours=3)
        if datetime.utcnow() < next_overtime:
            remaining = next_overtime - datetime.utcnow()
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            seconds = remaining.seconds % 60
            flash(f'You need to wait {hours}h {minutes}m {seconds}s before doing overtime again.', 'warning')
            return redirect(url_for('main.profile'))
    
    # Calculate reward based on level
    reward = 750 + (current_user.level * 75)
    
    # Update user's cash and last_overtime
    current_user.cash += reward
    current_user.last_overtime = datetime.utcnow()
    
    # Add XP for overtime
    current_user.add_xp(15)
    
    # Record the transaction
    GameHistory.record_game(
        user_id=current_user.id,
        game_type='overtime',
        bet_amount=0,
        outcome='reward',
        winnings=reward
    )
    
    db.session.commit()
    
    flash(f'You put in overtime and earned {reward} coins and 15 XP!', 'success')
    return redirect(url_for('main.profile'))
    
@main_bp.route('/weekly')
@login_required
def weekly():
    # Check if cooldown has passed (7 days)
    if current_user.last_weekly:
        next_weekly = current_user.last_weekly + timedelta(days=7)
        if datetime.utcnow() < next_weekly:
            remaining = next_weekly - datetime.utcnow()
            days = remaining.days
            hours = remaining.seconds // 3600
            flash(f'You need to wait {days}d {hours}h before claiming your weekly reward.', 'warning')
            return redirect(url_for('main.profile'))
    
    # Calculate reward based on level
    base_reward = 5000 + (current_user.level * 500)
    # Add randomness (1-2x multiplier)
    import random
    multiplier = 1 + random.random()
    reward = int(base_reward * multiplier)
    
    # Update user's cash and last_weekly
    current_user.cash += reward
    current_user.last_weekly = datetime.utcnow()
    
    # Add XP for weekly collection
    current_user.add_xp(50)
    
    # Record the transaction
    GameHistory.record_game(
        user_id=current_user.id,
        game_type='weekly',
        bet_amount=0,
        outcome='reward',
        winnings=reward
    )
    
    db.session.commit()
    
    flash(f'You received your weekly reward of {reward} coins and 50 XP!', 'success')
    return redirect(url_for('main.profile'))
    
@main_bp.route('/monthly')
@login_required
def monthly():
    # Check if cooldown has passed (30 days)
    if current_user.last_monthly:
        next_monthly = current_user.last_monthly + timedelta(days=30)
        if datetime.utcnow() < next_monthly:
            remaining = next_monthly - datetime.utcnow()
            days = remaining.days
            hours = remaining.seconds // 3600
            flash(f'You need to wait {days}d {hours}h before claiming your monthly reward.', 'warning')
            return redirect(url_for('main.profile'))
    
    # Calculate reward based on level
    base_reward = 25000 + (current_user.level * 2500)
    # Add randomness (1-2x multiplier)
    import random
    multiplier = 1 + random.random()
    reward = int(base_reward * multiplier)
    
    # Update user's cash and last_monthly
    current_user.cash += reward
    current_user.last_monthly = datetime.utcnow()
    
    # Add XP for monthly collection
    current_user.add_xp(200)
    
    # Record the transaction
    GameHistory.record_game(
        user_id=current_user.id,
        game_type='monthly',
        bet_amount=0,
        outcome='reward',
        winnings=reward
    )
    
    db.session.commit()
    
    flash(f'You received your monthly reward of {reward} coins and 200 XP!', 'success')
    return redirect(url_for('main.profile'))
    
@main_bp.route('/yearly')
@login_required
def yearly():
    # Check if cooldown has passed (365 days)
    if current_user.last_yearly:
        next_yearly = current_user.last_yearly + timedelta(days=365)
        if datetime.utcnow() < next_yearly:
            remaining = next_yearly - datetime.utcnow()
            days = remaining.days
            flash(f'You need to wait {days} days before claiming your yearly reward.', 'warning')
            return redirect(url_for('main.profile'))
    
    # Calculate reward based on level
    base_reward = 1000000 + (current_user.level * 25000)
    # Add randomness (1-2x multiplier)
    import random
    multiplier = 1 + random.random()
    reward = int(base_reward * multiplier)
    
    # Update user's cash and last_yearly
    current_user.cash += reward
    current_user.last_yearly = datetime.utcnow()
    
    # Add XP for yearly collection
    current_user.add_xp(1000)
    
    # Record the transaction
    GameHistory.record_game(
        user_id=current_user.id,
        game_type='yearly',
        bet_amount=0,
        outcome='reward',
        winnings=reward
    )
    
    db.session.commit()
    
    flash(f'You received your YEARLY JACKPOT of {reward} coins and 1000 XP!', 'success')
    return redirect(url_for('main.profile'))
