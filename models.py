from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    cash = db.Column(db.Integer, default=1000)
    level = db.Column(db.Integer, default=0)
    xp = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_daily = db.Column(db.DateTime, nullable=True)
    last_work = db.Column(db.DateTime, nullable=True)
    last_weekly = db.Column(db.DateTime, nullable=True)
    last_monthly = db.Column(db.DateTime, nullable=True)
    last_yearly = db.Column(db.DateTime, nullable=True)
    last_overtime = db.Column(db.DateTime, nullable=True)
    
    games = db.relationship('GameHistory', backref='player', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def add_cash(self, amount):
        self.cash += amount
        db.session.commit()
        
    def add_xp(self, amount):
        self.xp += amount
        # Check if level up is needed
        xp_needed = (self.level + 1) * 1000
        if self.xp >= xp_needed:
            self.level += 1
            self.xp -= xp_needed
        db.session.commit()
        
    def can_afford(self, amount):
        return self.cash >= amount

class GameHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    game_type = db.Column(db.String(50), nullable=False)
    bet_amount = db.Column(db.Integer, nullable=False)
    outcome = db.Column(db.String(50), nullable=False)  # 'win' or 'loss'
    winnings = db.Column(db.Integer, nullable=False)  # Can be negative for losses
    played_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @classmethod
    def record_game(cls, user_id, game_type, bet_amount, outcome, winnings):
        game = cls(
            user_id=user_id,
            game_type=game_type,
            bet_amount=bet_amount,
            outcome=outcome,
            winnings=winnings
        )
        db.session.add(game)
        db.session.commit()
        return game

class Leaderboard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'cash', 'blackjack_wins', etc.
    value = db.Column(db.Integer, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('leaderboard_entries', lazy=True))
    
class Mine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    name = db.Column(db.String(64), nullable=False)
    prestige_level = db.Column(db.Integer, default=0)
    
    # Resources
    coal = db.Column(db.Integer, default=0)
    iron = db.Column(db.Integer, default=0)
    gold = db.Column(db.Integer, default=0)
    diamond = db.Column(db.Integer, default=0)
    emerald = db.Column(db.Integer, default=0)
    lapis = db.Column(db.Integer, default=0)
    redstone = db.Column(db.Integer, default=0)
    
    # Unprocessed materials
    unprocessed_material = db.Column(db.Integer, default=0)
    
    # Mine units and upgrades
    diggers = db.Column(db.Integer, default=1)  # Start with 1 basic digger
    processors = db.Column(db.Integer, default=0)
    excavators = db.Column(db.Integer, default=0)
    drills = db.Column(db.Integer, default=0)
    
    # Crafting packs
    tech_packs = db.Column(db.Integer, default=0)
    utility_packs = db.Column(db.Integer, default=0)
    production_packs = db.Column(db.Integer, default=0)
    
    # Efficiency upgrades
    dig_efficiency = db.Column(db.Integer, default=1)
    processing_efficiency = db.Column(db.Integer, default=1)
    
    # Last dig time for cooldown
    last_dig = db.Column(db.DateTime, nullable=True)
    
    # Relationship with user
    user = db.relationship('User', backref=db.backref('mine', uselist=False, lazy=True))
    
    def dig(self):
        """Simulate digging to find resources"""
        import random
        
        # Base amounts based on equipment
        base_coal = 5 * self.diggers * self.dig_efficiency
        base_iron = 2 * self.diggers * self.dig_efficiency
        base_gold = 1 * self.diggers * self.dig_efficiency
        base_um = 3 * self.diggers * self.dig_efficiency
        
        # Add randomness (80% to 120% of base value)
        coal_found = int(base_coal * random.uniform(0.8, 1.2))
        iron_found = int(base_iron * random.uniform(0.8, 1.2))
        gold_found = int(base_gold * random.uniform(0.8, 1.2))
        um_found = int(base_um * random.uniform(0.8, 1.2))
        
        # Better equipment increases rare finds chance
        if self.excavators > 0 and random.random() < 0.1 * self.excavators:
            gold_found += random.randint(1, 3) * self.excavators
            
        if self.drills > 0 and random.random() < 0.05 * self.drills:
            um_found += random.randint(2, 5) * self.drills
        
        # Update resources
        self.coal += coal_found
        self.iron += iron_found
        self.gold += gold_found
        self.unprocessed_material += um_found
        
        # Update last dig time
        self.last_dig = datetime.utcnow()
        db.session.commit()
        
        return {
            'coal': coal_found,
            'iron': iron_found,
            'gold': gold_found,
            'unprocessed_material': um_found
        }
        
    def process_materials(self):
        """Process unprocessed materials into valuable resources"""
        import random
        
        if self.unprocessed_material <= 0:
            return None
            
        # Number of materials to process
        to_process = self.unprocessed_material
        
        # Base chances for each resource
        diamond_chance = 0.02 * self.processing_efficiency
        emerald_chance = 0.01 * self.processing_efficiency
        lapis_chance = 0.03 * self.processing_efficiency
        redstone_chance = 0.05 * self.processing_efficiency
        
        # Processors increase chances
        if self.processors > 0:
            diamond_chance *= (1 + 0.1 * self.processors)
            emerald_chance *= (1 + 0.1 * self.processors)
            lapis_chance *= (1 + 0.1 * self.processors)
            redstone_chance *= (1 + 0.1 * self.processors)
        
        # Calculate results
        diamonds_found = 0
        emeralds_found = 0
        lapis_found = 0
        redstone_found = 0
        
        for _ in range(to_process):
            roll = random.random()
            if roll < diamond_chance:
                diamonds_found += 1
            elif roll < diamond_chance + emerald_chance:
                emeralds_found += 1
            elif roll < diamond_chance + emerald_chance + lapis_chance:
                lapis_found += 1
            elif roll < diamond_chance + emerald_chance + lapis_chance + redstone_chance:
                redstone_found += 1
        
        # Update resources
        self.diamond += diamonds_found
        self.emerald += emeralds_found
        self.lapis += lapis_found
        self.redstone += redstone_found
        self.unprocessed_material = 0  # All materials processed
        
        db.session.commit()
        
        return {
            'diamond': diamonds_found,
            'emerald': emeralds_found,
            'lapis': lapis_found,
            'redstone': redstone_found
        }
        
    def craft_pack(self, pack_type, amount=1):
        """Craft a pack using resources"""
        required_resources = {
            'tech': {
                'iron': 10 * amount,
                'gold': 5 * amount,
                'redstone': 2 * amount
            },
            'utility': {
                'iron': 15 * amount,
                'coal': 20 * amount,
                'lapis': 2 * amount
            },
            'production': {
                'iron': 20 * amount,
                'gold': 10 * amount,
                'diamond': 1 * amount
            }
        }
        
        # Validate pack type
        if pack_type not in ['tech', 'utility', 'production']:
            return {'success': False, 'message': 'Invalid pack type'}
        
        # Check if user has enough resources
        resources = required_resources[pack_type]
        for resource, required in resources.items():
            resource_value = getattr(self, resource, 0)
            if resource_value < required:
                return {'success': False, 'message': f'Not enough {resource}. Need {required}, have {resource_value}'}
                
        # Subtract resources
        for resource, required in resources.items():
            current = getattr(self, resource)
            setattr(self, resource, current - required)
            
        # Add pack
        if pack_type == 'tech':
            self.tech_packs += amount
        elif pack_type == 'utility':
            self.utility_packs += amount
        elif pack_type == 'production':
            self.production_packs += amount
            
        db.session.commit()
        
        return {'success': True, 'message': f'Successfully crafted {amount} {pack_type} pack(s)'}
            
    def buy_upgrade(self, upgrade_type, amount=1):
        """Buy mine upgrades using coins"""
        upgrade_costs = {
            'digger': 500,
            'processor': 1000,
            'excavator': 2500,
            'drill': 5000,
            'dig_efficiency': 1500,
            'processing_efficiency': 2000
        }
        
        # Validate upgrade type
        if upgrade_type not in upgrade_costs:
            return {'success': False, 'message': 'Invalid upgrade type'}
            
        # Calculate total cost
        base_cost = upgrade_costs[upgrade_type]
        
        # Progressive cost increase for equipment upgrades
        current_level = getattr(self, upgrade_type + 's' if upgrade_type in ['digger', 'processor', 'excavator', 'drill'] else upgrade_type)
        
        # Calculate total cost with scaling
        total_cost = 0
        for i in range(amount):
            level_cost = int(base_cost * (1 + 0.1 * (current_level + i)))
            total_cost += level_cost
            
        # Check if user can afford
        user = User.query.get(self.user_id)
        if user.cash < total_cost:
            return {'success': False, 'message': f'Not enough coins. Need {total_cost}, have {user.cash}'}
            
        # Process purchase
        user.cash -= total_cost
        
        if upgrade_type in ['digger', 'processor', 'excavator', 'drill']:
            attr_name = upgrade_type + 's'  # plural form for equipment count
        else:
            attr_name = upgrade_type
            
        current = getattr(self, attr_name)
        setattr(self, attr_name, current + amount)
        
        db.session.commit()
        
        return {
            'success': True, 
            'message': f'Successfully purchased {amount} {upgrade_type}(s)',
            'cost': total_cost
        }
