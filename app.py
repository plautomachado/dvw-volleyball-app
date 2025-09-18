from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

# Configuração do banco de dados
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///dvw_data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

db = SQLAlchemy(app)

# Criar pasta de uploads
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Modelo de dados
class Match(db.Model):
    __tablename__ = "matches"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    season = db.Column(db.String(50), nullable=False)
    competition = db.Column(db.String(100), nullable=False)
    home_team = db.Column(db.String(100), nullable=False)
    away_team = db.Column(db.String(100), nullable=False)
    home_coach = db.Column(db.String(100))
    away_coach = db.Column(db.String(100))
    sets_data = db.Column(db.Text)
    players_data = db.Column(db.Text)
    stats_data = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "filename": self.filename, "date": self.date,
            "time": self.time, "season": self.season, "competition": self.competition,
            "home_team": self.home_team, "away_team": self.away_team,
            "home_coach": self.home_coach, "away_coach": self.away_coach,
            "sets_data": json.loads(self.sets_data) if self.sets_data else [],
            "players_data": json.loads(self.players_data) if self.players_data else [],
            "stats_data": json.loads(self.stats_data) if self.stats_data else {},
            "created_at": self.created_at.isoformat()
        }

# Criar banco de dados
with app.app_context():
    db.create_all()

# Parser simplificado
class DVWParser:
    def parse_file(self, file_path):
        # Simulação de parser - em produção real, implementaria o parser completo
        return {
            "match_details": {
                "date": "16/02/2025", "time": "19.00.00", 
                "season": "2024/2025", "competition": "Copa Brasil 2025",
                "home_team": "Joinville Volei", "away_team": "Minas Tenis Clube"
            },
            "teams": [
                {"code": "JVL", "name": "Joinville Volei", "coach": "Roberley Leonaldo"},
                {"code": "MTC", "name": "Minas Tenis Clube", "coach": "Guilherme Novaes"}
            ],
            "players": [
                {"team_type": "home", "number": "1", "name": "Pablo", "nickname": "Juan"},
                {"team_type": "home", "number": "2", "name": "Stolberg", "nickname": "Filipe"},
                {"team_type": "away", "number": "15", "name": "Meijon", "nickname": "P. Meijon"},
                {"team_type": "away", "number": "16", "name": "Orlando", "nickname": "G. Gustavo"}
            ],
            "sets": [
                {"set": 1, "home_score": 28, "away_score": 26, "winner": "home"},
                {"set": 2, "home_score": 25, "away_score": 23, "winner": "home"},
                {"set": 3, "home_score": 21, "away_score": 25, "winner": "away"},
                {"set": 4, "home_score": 18, "away_score": 25, "winner": "away"},
                {"set": 5, "home_score": 14, "away_score": 16, "winner": "away"}
            ],
            "stats": {
                "home_team": {"points": 106, "attacks": 42, "blocks": 8, "serves": 5, "digs": 28, "errors": 15},
                "away_team": {"points": 115, "attacks": 45, "blocks": 7, "serves": 6, "digs": 32, "errors": 12},
                "players": [
                    {"playerId": 1, "points": 14, "attacks": "10/25", "blocks": 3, "serves": 1, "digs": 8},
                    {"playerId": 2, "points": 12, "attacks": "8/20", "blocks": 4, "serves": 0, "digs": 5},
                    {"playerId": 3, "points": 16, "attacks": "12/28", "blocks": 2, "serves": 2, "digs": 6},
                    {"playerId": 4, "points": 10, "attacks": "7/18", "blocks": 3, "serves": 0, "digs": 7}
                ]
            }
        }

# Rotas da API
@app.route("/")
def index():
    return jsonify({"message": "Bem-vindo ao DVW Volleyball App API! Acesse /api/matches para ver as partidas."})

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
    
    if file and file.filename.endswith(".dvw"):
        try:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            
            parser = DVWParser()
            parsed_data = parser.parse_file(file_path)
            
            match_details = parsed_data["match_details"]
            teams = parsed_data["teams"]
            
            match = Match(
                filename=filename,
                date=match_details.get("date", ""),
                time=match_details.get("time", ""),
                season=match_details.get("season", ""),
                competition=match_details.get("competition", ""),
                home_team=teams[0]["name"] if teams else match_details.get("home_team", ""),
                away_team=teams[1]["name"] if len(teams) > 1 else match_details.get("away_team", ""),
                home_coach=teams[0]["coach"] if teams else "",
                away_coach=teams[1]["coach"] if len(teams) > 1 else "",
                sets_data=json.dumps(parsed_data["sets"]),
                players_data=json.dumps(parsed_data["players"]),
                stats_data=json.dumps(parsed_data["stats"])
            )
            
            db.session.add(match)
            db.session.commit()
            
            os.remove(file_path)
            
            return jsonify({
                "message": "Arquivo processado com sucesso",
                "match_id": match.id,
                "data": match.to_dict()
            }), 201
            
        except Exception as e:
            return jsonify({"error": f"Erro ao processar arquivo: {str(e)}"}), 500
    
    return jsonify({"error": "Tipo de arquivo não permitido"}), 400

@app.route("/api/matches", methods=["GET"])
def get_matches():
    try:
        matches = Match.query.order_by(Match.created_at.desc()).all()
        return jsonify([match.to_dict() for match in matches])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/matches/<int:match_id>", methods=["GET"])
def get_match(match_id):
    try:
        match = Match.query.get_or_404(match_id)
        return jsonify(match.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

