from flask import Flask, request, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__, static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'
db = SQLAlchemy(app)

app.app_context().push()

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, nullable=False, unique=True)
    tFormat = db.Column(db.String(80), nullable=False)

class Contestant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player = db.Column(db.String(80), nullable=False)
    seed = db.Column(db.Integer, nullable=True)
    tournament_id = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('tournament_id', 'player', name='unique_tournament_player'),
    )

class MatchResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player1 = db.Column(db.String(80), nullable=False)
    player2 = db.Column(db.String(80), nullable=False)
    result = db.Column(db.String(80), nullable=False)
    tournament_id = db.Column(db.Integer, nullable=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/new')
def new():
    return render_template('new.html')

@app.route('/new/submit', methods=['POST'])
def create():
    data = request.form
    tournament_id = int(data['tournament_id'])
    existing_tournament = Tournament.query.filter_by(tournament_id=tournament_id).first()
    if existing_tournament:
        return redirect(url_for('duplicate'))
    
    tournament = Tournament(
        tournament_id=tournament_id,
        tFormat=data['format']
    )
    db.session.add(tournament)
    db.session.commit()
    return render_template('submission.html')

@app.route('/entry')
def entry():
    tournaments = Tournament.query.all()
    return render_template('entry.html', tournaments=tournaments)

@app.route('/entry/submit', methods=['POST'])
def register():
    data = request.form
    tournament_id = int(data['tournament_id'])
    existing_contestant = Contestant.query.filter_by(tournament_id=tournament_id, player=data['player']).first()
    if existing_contestant:
        return redirect(url_for('duplicate'))

    contestant = Contestant(
        player=data['player'],
        seed=data['seed'],
        tournament_id=tournament_id
    )
    db.session.add(contestant)
    db.session.commit()
    return render_template('submission.html')

@app.route('/match')
def match():
    tournaments = Tournament.query.all()
    return render_template('match.html', tournaments=tournaments)

@app.route('/match/submit', methods=['POST'])
def submit_result():
    data = request.form
    match_result = MatchResult(
        player1=data['player1'],
        player2=data['player2'],
        result=data['result'],
        tournament_id=data['tournament_id']
    )
    db.session.add(match_result)
    db.session.commit()
    return render_template('submission.html')

@app.route('/bracket', methods=['Get', 'POST'])
def bracket():
    if request.method == 'POST':
        tournament_id = request.form['id']
        return redirect(url_for('display', id=tournament_id))
    tournaments = Tournament.query.all()
    return render_template('bidselect.html', tournaments=tournaments)

@app.route('/bracket/<id>')
def display(id):
    return render_template('bracket.html', tournament_id=id)

@app.route('/players', methods=['GET', 'POST'])
def players():
    if request.method == 'POST':
        tournament_id = request.form['id']
        return redirect(url_for('displayer', id=tournament_id))
    tournaments = Tournament.query.all()
    return render_template('pidselect.html', tournaments=tournaments)

@app.route('/players/<id>', methods=['GET'])
def displayer(id):
    return render_template('players.html', contestants=Contestant.query.filter_by(tournament_id=id), id=id)

@app.route('/duplicate')
def duplicate():
    return render_template('duplicate.html')

if __name__ == '__main__':
    db.drop_all()
    db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
