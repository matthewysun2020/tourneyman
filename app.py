from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'
db = SQLAlchemy(app)

app.app_context().push()

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, nullable=False)
    tFormat = db.Column(db.String(80), nullable=False)

class Contestant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    player = db.Column(db.String(80), nullable=False)
    seed = db.Column(db.Integer, nullable=True)
    tournament_id = db.Column(db.Integer, nullable=False)

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
    tournament = Tournament(
        tournament_id=data['tournament_id'],
        tFormat=data['format']
    )
    db.session.add(tournament)
    db.session.commit()
    return render_template('submission.html')

@app.route('/entry')
def entry():
    return render_template('entry.html')

@app.route('/entry/submit', methods=['POST'])
def register():
    data = request.form
    contestant = Contestant(
        player=data['player'],
        seed=data['seed'],
        tournament_id=data['tournament_id']
    )
    db.session.add(contestant)
    db.session.commit()
    return render_template('submission.html')

@app.route('/match')
def match():
    return render_template('match.html')

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

@app.route('/bracket')
def bracket():
    # TODO: Needs to be restructured. Return based on tournament ID.
    # Find each unique tournament ID here, then render new HTML once selection is made
    return render_template('bidselect.html', tournaments=Tournament.query.all())

@app.route('/bracket/<id>')
def display(id):
    # TODO: Display specific bracket of tournament with ID, with proper format.
    # Need to somehow store tournament format with ID, then pass it to the HTML page.
    return True

@app.route('/players')
def players():
    return render_template('pidselect.html', tournaments=Tournament.query.all())

@app.route('/players/<id>')
def displayer(id):
    return render_template('players.html', contestants=Contestant.query.filter_by(tournament_id=id))

if __name__ == '__main__':
    db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
