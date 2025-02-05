from flask import Flask, request, render_template, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from enum import Enum
import math

app = Flask(__name__, static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'
db = SQLAlchemy(app)

app.app_context().push()

class TournamentFormat(Enum):
    SINGLE_ELIMINATION = 'single_elimination'
    DOUBLE_ELIMINATION = 'double_elimination'
    ROUND_ROBIN = 'round_robin'
    SWISS = 'swiss'

class PlayerStatus(Enum):
    WINNERS_BRACKET = 'winners_bracket'
    LOSERS_BRACKET = 'losers_bracket'
    ELIMINATED = 'eliminated'

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    tFormat = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='PENDING')  # PENDING, ACTIVE, COMPLETED
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    current_winners_round = db.Column(db.Integer, default=1)
    current_losers_round = db.Column(db.Integer, default=0)  # 0 means no losers bracket yet
    current_round = db.Column(db.Integer, default=1)  # For non-bracket formats
    contestants = db.relationship('Contestant', backref='tournament', lazy=True)
    matches = db.relationship('MatchResult', backref='tournament', lazy=True)

    @property
    def is_elimination_format(self):
        return self.tFormat in [TournamentFormat.SINGLE_ELIMINATION.value, TournamentFormat.DOUBLE_ELIMINATION.value]

    @property
    def is_double_elimination(self):
        return self.tFormat == TournamentFormat.DOUBLE_ELIMINATION.value

    @property
    def total_rounds_needed(self):
        """Calculate total rounds needed based on format and player count"""
        player_count = len([c for c in self.contestants if c.active])
        if self.tFormat == TournamentFormat.ROUND_ROBIN.value:
            return player_count - 1
        elif self.tFormat == TournamentFormat.SWISS.value:
            # Swiss typically uses log2(N) rounds, rounded up
            return math.ceil(math.log2(player_count))
        return None  # For elimination formats

    def get_swiss_pairings(self):
        """Generate Swiss-system Monrad pairings for the current round"""
        if self.tFormat != TournamentFormat.SWISS.value:
            raise ValueError("Tournament is not Swiss format")

        # Get active players and sort by score, then seed
        players = sorted(
            [p for p in self.contestants if p.active],
            key=lambda x: (-x.score, x.seed or float('inf'))
        )
        
        # Get all previous matches to avoid repeats
        previous_matches = {
            (m.player1, m.player2) for m in self.matches
        }
        
        pairings = []
        unpaired = players.copy()
        
        while len(unpaired) >= 2:
            player1 = unpaired.pop(0)
            
            # Find the highest-ranked opponent that player1 hasn't faced
            for i, player2 in enumerate(unpaired):
                if (player1.player, player2.player) not in previous_matches and \
                   (player2.player, player1.player) not in previous_matches:
                    unpaired.pop(i)
                    pairings.append((player1, player2))
                    break
            else:
                # If no valid opponent found, pair with the next available player
                player2 = unpaired.pop(0)
                pairings.append((player1, player2))
        
        # Handle odd number of players with a bye
        if unpaired:
            pairings.append((unpaired[0], None))
        
        return pairings

    def get_round_robin_pairings(self):
        """Generate Round Robin pairings for the current round using Circle method"""
        if self.tFormat != TournamentFormat.ROUND_ROBIN.value:
            raise ValueError("Tournament is not Round Robin format")

        players = [p for p in self.contestants if p.active]
        if len(players) % 2 != 0:
            players.append(None)  # Add a bye slot for odd number of players
        
        n = len(players)
        round_num = self.current_round
        
        # Create the initial circle arrangement
        circle = players[:1] + players[1:][:(n-1)][::-1]
        
        # Rotate (round_num - 1) times
        for _ in range(round_num - 1):
            circle = [circle[0]] + [circle[-1]] + circle[1:-1]
        
        # Generate pairings
        pairings = []
        for i in range(n // 2):
            if circle[i] is not None and circle[n-1-i] is not None:
                pairings.append((circle[i], circle[n-1-i]))
            elif circle[i] is not None:
                pairings.append((circle[i], None))  # Bye
            elif circle[n-1-i] is not None:
                pairings.append((circle[n-1-i], None))  # Bye
        
        return pairings

class Contestant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player = db.Column(db.String(80), nullable=False)
    seed = db.Column(db.Integer, nullable=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.tournament_id'), nullable=False)
    score = db.Column(db.Float, default=0.0)
    matches_played = db.Column(db.Integer, default=0)
    matches_won = db.Column(db.Integer, default=0)
    matches_drawn = db.Column(db.Integer, default=0)  # For Swiss/Round Robin
    losses = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), nullable=True)  # Nullable for non-bracket formats
    matches_as_player1 = db.relationship('MatchResult', 
                                       foreign_keys='MatchResult.player1_id',
                                       backref='player1_contestant',
                                       lazy=True)
    matches_as_player2 = db.relationship('MatchResult',
                                       foreign_keys='MatchResult.player2_id',
                                       backref='player2_contestant',
                                       lazy=True)

    __table_args__ = (
        db.UniqueConstraint('tournament_id', 'player', name='unique_tournament_player'),
    )

    @property
    def player_matches(self):
        return self.matches_as_player1 + self.matches_as_player2

    def handle_match_result(self, won, is_bye=False, is_draw=False):
        """Handle match result based on tournament format"""
        tournament = Tournament.query.filter_by(tournament_id=self.tournament_id).first()
        
        self.matches_played += 1
        if is_draw:
            self.matches_drawn += 1
            self.score += 0.5
        elif won:
            self.matches_won += 1
            self.score += 1
        else:
            self.losses += 1
            if tournament.is_elimination_format:
                self.handle_loss()

    def handle_loss(self):
        """Handle the logic when a contestant loses a match."""
        tournament = Tournament.query.filter_by(tournament_id=self.tournament_id).first()
        if tournament.is_elimination_format:
            self.status = PlayerStatus.ELIMINATED.value
            self.active = False
        db.session.commit()

class MatchResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.tournament_id'), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    bracket = db.Column(db.String(20), nullable=True)  # Nullable for non-bracket formats
    player1_id = db.Column(db.Integer, db.ForeignKey('contestant.id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('contestant.id'), nullable=True)  # Nullable for byes
    player1 = db.Column(db.String(80), nullable=False)
    player2 = db.Column(db.String(80), nullable=True)  # Nullable for byes
    winner = db.Column(db.String(80), nullable=True)
    loser = db.Column(db.String(80), nullable=True)
    score = db.Column(db.String(100), nullable=True)
    is_draw = db.Column(db.Boolean, default=False)  # For Swiss/Round Robin
    status = db.Column(db.String(20), nullable=False, default='SCHEDULED')
    scheduled_time = db.Column(db.DateTime, nullable=True)
    completion_time = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.CheckConstraint(
            """
            (player2 IS NULL AND status = 'BYE' AND winner = player1 AND loser IS NULL) OR 
            (player2 IS NOT NULL AND status != 'BYE' AND 
             ((is_draw = true AND winner IS NULL AND loser IS NULL) OR
              (is_draw = false AND winner IN (player1, player2) AND loser IN (player1, player2))))
            """,
            name='valid_match_state'
        ),
    )

def register_bye(tournament_id, player_name):
    """Register a bye for a player in the current round."""
    try:
        tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
        player = Contestant.query.filter_by(tournament_id=tournament_id, player=player_name, active=True).first_or_404()
        
        # Check if player already has a match in this round
        existing_match = MatchResult.query.filter(
            MatchResult.tournament_id == tournament_id,
            MatchResult.round_number == tournament.current_round,
            db.or_(
                MatchResult.player1 == player_name,
                MatchResult.player2 == player_name
            )
        ).first()
        
        if existing_match:
            raise ValueError(f"Player {player_name} already has a match in round {tournament.current_round}")
        
        # Create bye match
        match = MatchResult(
            tournament_id=tournament_id,
            round_number=tournament.current_round,
            bracket='winners',
            player1_id=player.id,
            player1=player_name,
            status='BYE',
            winner=player_name,
            completion_time=datetime.now()
        )
        
        # Update player statistics
        player.matches_played += 1
        player.matches_won += 1
        player.score += 1
        
        db.session.add(match)
        db.session.commit()
        
        # Get the tournament by ID
        tournament = Tournament.query.filter_by(tournament_id=tournament_id).first()
        
        # Check active players
        active_players = [c for c in tournament.contestants if c.active]
        if len(active_players) == 1:
            tournament.status = 'COMPLETED'
            db.session.commit()
        
        # Check if round is complete
        check_round_completion(tournament_id)
        
        return True
    except Exception as e:
        db.session.rollback()
        raise e

def check_round_completion(tournament_id):
    """Check if all players in the current round have matches and increment round if needed."""
    tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
    active_players = Contestant.query.filter_by(tournament_id=tournament_id, active=True).all()
    
    # Get all matches for the current round
    current_round = tournament.current_winners_round if tournament.is_elimination_format else tournament.current_round
    current_round_matches = MatchResult.query.filter_by(
        tournament_id=tournament_id,
        round_number=current_round
    ).all()
    
    # Count players who have matches in current round
    players_with_matches = set()
    for match in current_round_matches:
        players_with_matches.add(match.player1)
        if match.player2:  # Don't add None for byes
            players_with_matches.add(match.player2)
    
    # Check if all active players have matches
    active_player_names = {player.player for player in active_players}
    if players_with_matches == active_player_names:
        # All players have matches, check if we should increment round
        if tournament.is_elimination_format:
            tournament.current_winners_round += 1
        else:
            # For Round Robin and Swiss, check if we've reached the total rounds
            if tournament.total_rounds_needed and tournament.current_round >= tournament.total_rounds_needed:
                tournament.status = 'COMPLETED'
            else:
                tournament.current_round += 1
        
        db.session.commit()
        return True
    
    return False

@app.route('/')
def index():
    """Home page."""
    # Get active tournaments
    active_tournaments = Tournament.query.filter(
        Tournament.status.in_(['PENDING', 'ACTIVE'])
    ).order_by(Tournament.start_date.desc()).all()
    
    # Get recent players (players who have participated in the last 5 tournaments)
    recent_tournaments = Tournament.query.order_by(
        Tournament.start_date.desc()
    ).limit(5).all()
    
    recent_player_ids = set()
    recent_players = []
    
    for tournament in recent_tournaments:
        for contestant in tournament.contestants:
            if contestant.player not in recent_player_ids:
                recent_player_ids.add(contestant.player)
                recent_players.append(contestant)
    
    # Sort players by matches played (descending)
    recent_players.sort(key=lambda x: x.matches_played, reverse=True)
    
    return render_template(
        'index.html',
        active_tournaments=active_tournaments,
        recent_players=recent_players[:10]  # Show top 10 recent players
    )

@app.route('/new')
def new():
    # Set min datetime to current time
    current_time = datetime.now().strftime('%Y-%m-%dT%H:%M')
    return render_template('new.html', min_datetime=current_time)

@app.route('/new/submit', methods=['POST'])
def create():
    try:
        data = request.form
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%dT%H:%M')
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%dT%H:%M')
        current_time = datetime.now()

        # Generate tournament ID using timestamp and name hash
        timestamp = int(current_time.timestamp())
        name_hash = sum(ord(c) for c in data['name']) % 1000
        tournament_id = timestamp * 1000 + name_hash

        # Determine status based on dates
        if current_time < start_date:
            status = 'PENDING'
        elif current_time <= end_date:
            status = 'ACTIVE'
        else:
            status = 'COMPLETED'

        tournament = Tournament(
            tournament_id=tournament_id,
            name=data['name'],
            tFormat=data['format'],
            status=status,
            start_date=start_date,
            end_date=end_date,
            current_round=1
        )
        
        db.session.add(tournament)
        db.session.commit()
        
        return redirect(url_for('tournaments'))
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/tournaments')
def tournaments():
    tournaments = Tournament.query.all()
    current_time = datetime.now()
    
    # Update tournament statuses based on current time
    for tournament in tournaments:
        if tournament.status != 'COMPLETED':
            if current_time < tournament.start_date:
                new_status = 'PENDING'
            elif current_time <= tournament.end_date:
                new_status = 'ACTIVE'
            else:
                new_status = 'COMPLETED'
                
            if new_status != tournament.status:
                tournament.status = new_status
    
    tournaments = sorted(tournaments, key=lambda x: (x.status != 'ACTIVE', x.status != 'PENDING', x.start_date), reverse=True)
    
    db.session.commit()
    return render_template('tournaments.html', tournaments=tournaments)

@app.route('/tournaments/<int:tournament_id>')
def tournament_details(tournament_id):
    tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
    return render_template('tournament_details.html', tournament=tournament)

@app.route('/tournaments/<int:tournament_id>/add_player')
def add_player_page(tournament_id):
    tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
    return render_template('add_player.html', tournament=tournament)

@app.route('/tournaments/<int:tournament_id>/players')
def player_list(tournament_id):
    tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
    players = Contestant.query.filter_by(tournament_id=tournament_id).all()
    return render_template('player_list.html', tournament=tournament, players=players)

@app.route('/tournaments/<int:tournament_id>/match_management')
def match_management(tournament_id):
    """Match management page."""
    tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
    
    # Get active players
    active_players = Contestant.query.filter_by(
        tournament_id=tournament_id,
        active=True
    ).all()
    
    # Sort players alphabetically
    active_players.sort(key=lambda x: x.player.lower())
    
    # Create serializable player data for JavaScript
    serializable_players = []
    for contestant in active_players:
        serializable_players.append({
            'id': contestant.id,
            'player': contestant.player,
            'status': contestant.status or '',  # Handle None values
            'score': contestant.score,
            'matches_played': contestant.matches_played,
            'matches_won': contestant.matches_won,
            'matches_drawn': contestant.matches_drawn or 0  # Handle None values
        })
    
    return render_template(
        'match_management.html',
        tournament=tournament,
        active_players=active_players,  # For template rendering
        players=serializable_players,   # For JavaScript
        bracket='winners'  # Default to winners bracket
    )

@app.route('/tournaments/<int:tournament_id>/recent_matches')
def recent_matches(tournament_id):
    tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
    matches = MatchResult.query.filter_by(tournament_id=tournament_id).order_by(MatchResult.id.desc()).limit(10).all()
    return render_template('recent_matches.html', tournament=tournament, matches=matches)

@app.route('/tournaments/<int:tournament_id>/update')
def update_tournament_page(tournament_id):
    tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
    return render_template('update_tournament.html', tournament=tournament)

@app.route('/tournaments/<int:tournament_id>/bracket')
def bracket(tournament_id):
    tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
    return render_template('bracket.html', tournament=tournament)

@app.route('/tournaments/<int:tournament_id>/add_player', methods=['POST'])
def add_player(tournament_id):
    try:
        tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
        
        player = Contestant(
            player=request.form['player'],
            seed=request.form.get('seed'),
            tournament_id=tournament_id
        )
        
        db.session.add(player)
        db.session.commit()
        
        return redirect(url_for('tournament_details', tournament_id=tournament_id))
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/tournaments/<int:tournament_id>/remove_player', methods=['POST'])
def remove_player(tournament_id):
    try:
        player_name = request.form['player']
        reason = request.form['reason']
        
        player = Contestant.query.filter_by(
            tournament_id=tournament_id,
            player=player_name
        ).first_or_404()
        
        # Set player as inactive instead of deleting
        player.active = False
        
        # Get the tournament by ID
        tournament = Tournament.query.filter_by(tournament_id=tournament_id).first()
        
        # Check active players
        active_players = [c for c in tournament.contestants if c.active]
        if len(active_players) == 1:
            tournament.status = 'COMPLETED'
        
        db.session.commit()
        
        return redirect(url_for('tournament_details', tournament_id=tournament_id))
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/tournaments/<int:tournament_id>/submit_result', methods=['POST'])
def submit_result(tournament_id):
    try:
        tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
        data = request.form
        
        # Ensure players are different
        if data['player1'] == data['player2']:
            raise ValueError("Players must be different")
        
        # Check if either player already has a match in this round
        current_round = tournament.current_winners_round if tournament.is_elimination_format else tournament.current_round
        for player in [data['player1'], data['player2']]:
            existing_match = MatchResult.query.filter(
                MatchResult.tournament_id == tournament_id,
                MatchResult.round_number == current_round,
                db.or_(
                    MatchResult.player1 == player,
                    MatchResult.player2 == player
                )
            ).first()
            
            if existing_match:
                raise ValueError(f"Player {player} already has a match in round {current_round}")
        
        # Get player IDs
        player1 = Contestant.query.filter_by(player=data['player1'], tournament_id=tournament_id).first()
        player2 = Contestant.query.filter_by(player=data['player2'], tournament_id=tournament_id).first()
        
        if not player1 or not player2:
            raise ValueError("One or both players not found in tournament")
        
        # Handle draws for non-elimination formats
        is_draw = False
        if not tournament.is_elimination_format and data.get('is_draw') == 'true':
            is_draw = True
            winner = None
            loser = None
        else:
            # Determine winner from score
            scores = data['score'].split('-')
            if len(scores) != 2:
                raise ValueError("Invalid score format. Use X-Y format (e.g., 2-1)")
                
            score1, score2 = map(int, scores)
            winner = data['player1'] if score1 > score2 else data['player2']
            loser = data['player2'] if score1 > score2 else data['player1']
        
        # Create match result
        match = MatchResult(
            tournament_id=tournament_id,
            round_number=current_round,
            bracket='winners' if tournament.is_elimination_format else None,
            player1_id=player1.id,
            player2_id=player2.id,
            player1=player1.player,  # Use string value instead of Contestant object
            player2=player2.player,  # Use string value instead of Contestant object
            winner=winner,
            loser=loser,
            score=data['score'],
            is_draw=is_draw,
            status='COMPLETED',
            completion_time=datetime.now()
        )
        
        # Update player statistics
        if is_draw:
            # Both players get half a point
            player1.handle_match_result(won=False, is_draw=True)
            player2.handle_match_result(won=False, is_draw=True)
        else:
            # Update winner
            winner_obj = player1 if winner == player1.player else player2
            winner_obj.handle_match_result(won=True)
            
            # Update loser
            loser_obj = player2 if winner == player1.player else player1
            loser_obj.handle_match_result(won=False)
        
        db.session.add(match)
        db.session.commit()
        
        # Get the tournament by ID
        tournament = Tournament.query.filter_by(tournament_id=tournament_id).first()
        
        # Check active players
        active_players = [c for c in tournament.contestants if c.active]
        if len(active_players) == 1:
            tournament.status = 'COMPLETED'
            db.session.commit()
        
        # Check if round is complete and increment if needed
        check_round_completion(tournament_id)
        
        return redirect(url_for('tournament_details', tournament_id=tournament_id))
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/player/<player_name>')
def player_stats(player_name):
    """View player statistics."""
    # Get all tournaments and matches for the player
    player_tournaments = db.session.query(Tournament).join(
        Contestant, Tournament.tournament_id == Contestant.tournament_id
    ).filter(Contestant.player == player_name).all()
    
    # Calculate statistics
    total_matches = 0
    total_wins = 0
    tournaments_won = 0
    
    for tournament in player_tournaments:
        contestant = next(c for c in tournament.contestants if c.player == player_name)
        total_matches += contestant.matches_played
        total_wins += contestant.matches_won
        # Check if player won the tournament (highest score in completed tournament)
        if tournament.status == 'COMPLETED':
            max_score = max(c.score for c in tournament.contestants)
            if contestant.score == max_score:
                tournaments_won += 1
    
    win_rate = (total_wins / total_matches * 100) if total_matches > 0 else 0
    
    # Get all matches involving the player
    matches = db.session.query(MatchResult).filter(
        db.or_(
            MatchResult.player1 == player_name,
            MatchResult.player2 == player_name
        )
    ).order_by(MatchResult.completion_time.desc()).all()
    
    return render_template(
        'player_stats.html',
        player_name=player_name,
        tournaments=player_tournaments,
        matches=matches,
        total_matches=total_matches,
        total_wins=total_wins,
        tournaments_won=tournaments_won,
        win_rate=round(win_rate, 2)
    )

@app.route('/tournaments/<int:tournament_id>/add_players', methods=['GET', 'POST'])
def add_players(tournament_id):
    """Add existing players to a tournament."""
    tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
    
    if request.method == 'POST':
        try:
            selected_players = request.form.getlist('players')
            if not selected_players:
                raise ValueError("No players selected")
            
            # Get existing contestants
            existing_players = {c.player for c in tournament.contestants}
            
            # Add new contestants
            for player in selected_players:
                if player not in existing_players:
                    contestant = Contestant(
                        tournament_id=tournament_id,
                        player=player,
                        registration_time=datetime.now(),
                        active=True,
                        matches_played=0,
                        matches_won=0,
                        matches_drawn=0,
                        score=0
                    )
                    db.session.add(contestant)
            
            db.session.commit()
            flash('Players added successfully!', 'success')
            return redirect(url_for('tournament_details', tournament_id=tournament_id))
            
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('add_players', tournament_id=tournament_id))
    
    # Get all unique players from past tournaments
    all_players = db.session.query(Contestant.player).distinct().all()
    all_players = [p[0] for p in all_players]
    # Remove players already in tournament
    existing_players = {c.player for c in tournament.contestants}
    available_players = sorted([p for p in all_players if p not in existing_players])
    
    return render_template(
        'add_players.html',
        tournament=tournament,
        available_players=available_players
    )

@app.route('/tournaments/<int:tournament_id>/update', methods=['POST'])
def update_tournament(tournament_id):
    try:
        tournament = Tournament.query.filter_by(tournament_id=tournament_id).first_or_404()
        data = request.form
        
        # Update fields if provided
        if data.get('name'):
            tournament.name = data['name']
        if data.get('format'):
            tournament.tFormat = data['format']
        if data.get('start_date'):
            tournament.start_date = datetime.strptime(data['start_date'], '%Y-%m-%dT%H:%M')
        if data.get('end_date'):
            tournament.end_date = datetime.strptime(data['end_date'], '%Y-%m-%dT%H:%M')
        if data.get('current_round'):
            tournament.current_round = int(data['current_round'])
            
        if tournament.status != 'COMPLETED':
            # Update status based on new dates
            current_time = datetime.now()
            if current_time < tournament.start_date:
                tournament.status = 'PENDING'
            elif current_time <= tournament.end_date:
                tournament.status = 'ACTIVE'
            else:
                tournament.status = 'COMPLETED'
            
        db.session.commit()
        return redirect(url_for('tournament_details', tournament_id=tournament_id))
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/tournaments/<int:tournament_id>/register_bye', methods=['POST'])
def register_bye_route(tournament_id):
    try:
        player_name = request.form['player']
        register_bye(tournament_id, player_name)
        return redirect(url_for('tournament_details', tournament_id=tournament_id))
    except Exception as e:
        return render_template('error.html', error=str(e))

@app.cli.command('reset_db')
def reset_db():
    """Reset the database."""
    db.drop_all()
    db.create_all()
    print('Database reset successfully.')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
