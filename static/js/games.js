// Shared game functions
function formatBet(amount) {
    return new Intl.NumberFormat().format(amount);
}

// CoinFlip Game
function initCoinFlip() {
    const coinFlipForm = document.getElementById('coinflip-form');
    const coin = document.getElementById('coin');
    const resultDisplay = document.getElementById('result');
    
    if (!coinFlipForm) return;
    
    coinFlipForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const bet = document.getElementById('bet_amount').value;
        const choice = document.querySelector('input[name="choice"]:checked').value;
        
        if (!bet || bet < 1) {
            alert('Please enter a valid bet amount');
            return;
        }
        
        // Animate coin flip
        resultDisplay.textContent = 'Flipping...';
        coin.classList.add('flip');
        
        // Wait for animation to finish before submitting
        setTimeout(() => {
            coinFlipForm.submit();
        }, 2000);
    });
    
    // Reset animation when needed
    if (coin) {
        coin.addEventListener('animationend', function() {
            this.classList.remove('flip');
        });
    }
}

// Blackjack Game
function initBlackjack() {
    const blackjackForm = document.getElementById('blackjack-form');
    const gameArea = document.getElementById('blackjack-game');
    const playerHandElement = document.getElementById('player-hand');
    const dealerHandElement = document.getElementById('dealer-hand');
    const messageElement = document.getElementById('game-message');
    const hitButton = document.getElementById('hit-button');
    const standButton = document.getElementById('stand-button');
    const resetButton = document.getElementById('reset-button');
    
    if (!blackjackForm) return;
    
    let gameState = {
        betAmount: 0,
        playerHand: [],
        dealerHand: [],
        deck: [],
        state: 'betting'
    };
    
    blackjackForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const bet = document.getElementById('bet_amount').value;
        
        if (!bet || bet < 1) {
            alert('Please enter a valid bet amount');
            return;
        }
        
        gameState.betAmount = bet;
        
        // Initialize game
        fetch('/games/blackjack/play', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'deal',
                bet_amount: bet,
                game_state: 'betting'
            })
        })
        .then(response => response.json())
        .then(data => {
            // Update game state
            gameState.playerHand = data.player_hand;
            gameState.dealerHand = data.dealer_hand;
            gameState.deck = data.deck;
            gameState.state = data.game_state;
            
            // Hide form, show game
            blackjackForm.classList.add('d-none');
            gameArea.classList.remove('d-none');
            
            // Render hands
            renderPlayerHand();
            renderDealerHand(true); // Hide dealer's hole card
            
            // Update UI
            messageElement.textContent = data.message;
            hitButton.disabled = false;
            standButton.disabled = false;
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred starting the game');
        });
    });
    
    // Hit action
    if (hitButton) {
        hitButton.addEventListener('click', function() {
            if (gameState.state !== 'player_turn') return;
            
            fetch('/games/blackjack/play', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: 'hit',
                    bet_amount: gameState.betAmount,
                    player_hand: gameState.playerHand,
                    dealer_hand: gameState.dealerHand,
                    game_state: gameState.state,
                    deck: gameState.deck
                })
            })
            .then(response => response.json())
            .then(data => {
                // Update game state
                gameState.playerHand = data.player_hand;
                gameState.state = data.game_state;
                if (data.deck) gameState.deck = data.deck;
                
                // Render updated hand
                renderPlayerHand();
                
                // Update UI
                messageElement.textContent = data.message;
                
                // Check if game over
                if (data.game_state === 'game_over') {
                    endGame(data.result);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred');
            });
        });
    }
    
    // Stand action
    if (standButton) {
        standButton.addEventListener('click', function() {
            if (gameState.state !== 'player_turn') return;
            
            fetch('/games/blackjack/play', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: 'stand',
                    bet_amount: gameState.betAmount,
                    player_hand: gameState.playerHand,
                    dealer_hand: gameState.dealerHand,
                    game_state: gameState.state,
                    deck: gameState.deck
                })
            })
            .then(response => response.json())
            .then(data => {
                // Update game state
                gameState.dealerHand = data.dealer_hand;
                gameState.state = data.game_state;
                
                // Show all cards
                renderDealerHand(false);
                
                // Update UI
                messageElement.textContent = data.message;
                
                // End game
                endGame(data.result);
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred');
            });
        });
    }
    
    // Reset button
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            // Reset game state
            gameState = {
                betAmount: 0,
                playerHand: [],
                dealerHand: [],
                deck: [],
                state: 'betting'
            };
            
            // Show form, hide game
            blackjackForm.classList.remove('d-none');
            gameArea.classList.add('d-none');
            
            // Clear hands
            playerHandElement.innerHTML = '';
            dealerHandElement.innerHTML = '';
            
            // Reset UI
            messageElement.textContent = '';
            document.getElementById('bet_amount').value = '';
        });
    }
    
    function renderPlayerHand() {
        playerHandElement.innerHTML = '';
        gameState.playerHand.forEach(card => {
            const cardEl = createCardElement(card);
            playerHandElement.appendChild(cardEl);
        });
    }
    
    function renderDealerHand(hideHoleCard) {
        dealerHandElement.innerHTML = '';
        
        gameState.dealerHand.forEach((card, index) => {
            if (index === 1 && hideHoleCard) {
                // Create face-down card for hole card
                const cardEl = document.createElement('div');
                cardEl.className = 'card-container';
                cardEl.innerHTML = `
                    <div class="card">
                        <div class="card-back"></div>
                    </div>
                `;
                dealerHandElement.appendChild(cardEl);
            } else {
                const cardEl = createCardElement(card);
                dealerHandElement.appendChild(cardEl);
            }
        });
    }
    
    function createCardElement(card) {
        const cardEl = document.createElement('div');
        cardEl.className = 'card-container';
        
        const suitSymbol = getSuitSymbol(card.suit);
        const cardValue = getCardValue(card.value);
        
        cardEl.innerHTML = `
            <div class="card flipped">
                <div class="card-back"></div>
                <div class="card-front" style="color: ${card.suit === 'hearts' || card.suit === 'diamonds' ? 'red' : 'black'}">
                    <div class="card-value-top">${cardValue}</div>
                    <div class="card-suit">${suitSymbol}</div>
                    <div class="card-value-bottom">${cardValue}</div>
                </div>
            </div>
        `;
        
        return cardEl;
    }
    
    function getSuitSymbol(suit) {
        switch(suit) {
            case 'hearts': return '♥';
            case 'diamonds': return '♦';
            case 'clubs': return '♣';
            case 'spades': return '♠';
            default: return '';
        }
    }
    
    function getCardValue(value) {
        return value;
    }
    
    function endGame(result) {
        hitButton.disabled = true;
        standButton.disabled = true;
        resetButton.disabled = false;
        
        // Apply result styling
        if (result === 'win') {
            messageElement.classList.add('text-success');
        } else if (result === 'loss') {
            messageElement.classList.add('text-danger');
        } else {
            messageElement.classList.add('text-warning');
        }
    }
}

// Slots Game
function initSlots() {
    const slotsForm = document.getElementById('slots-form');
    const slotsContainer = document.getElementById('slots-container');
    const slot1 = document.getElementById('slot1');
    const slot2 = document.getElementById('slot2');
    const slot3 = document.getElementById('slot3');
    
    if (!slotsForm) return;
    
    slotsForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const bet = document.getElementById('bet_amount').value;
        
        if (!bet || bet < 1) {
            alert('Please enter a valid bet amount');
            return;
        }
        
        // Animate slots
        slot1.classList.add('spinning');
        slot2.classList.add('spinning');
        slot3.classList.add('spinning');
        slot1.textContent = '?';
        slot2.textContent = '?';
        slot3.textContent = '?';
        
        // Wait for animation then submit
        setTimeout(() => {
            slot1.classList.remove('spinning');
            slot2.classList.remove('spinning');
            slot3.classList.remove('spinning');
            
            slotsForm.submit();
        }, 1500);
    });
}

// Initialize games when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initCoinFlip();
    initBlackjack();
    initSlots();
});
