"""SQLite persistence for reproducible experiments."""
import json, sqlite3
from pathlib import Path
from cee.core.schemas import Candidate, Evaluation

class ExperimentStore:
    def __init__(self, path: str | Path = "cee_experiments.sqlite3"):
        self.path = str(path)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS candidates (
                fingerprint TEXT PRIMARY KEY, payload TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
            db.execute("""CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, fingerprint TEXT NOT NULL,
                task_id TEXT NOT NULL, score REAL NOT NULL, payload TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")

    def _connect(self):
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA journal_mode=WAL")
        return db

    def save_candidate(self, candidate: Candidate):
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO candidates(fingerprint,payload) VALUES (?,?)",
                (candidate.fingerprint, json.dumps(candidate.to_dict())))

    def save_evaluation(self, candidate: Candidate, evaluation: Evaluation):
        self.save_candidate(candidate)
        payload = {"candidate_id": evaluation.candidate_id, "task_id": evaluation.task_id,
            "score": evaluation.score, "output": evaluation.output,
            "latency_seconds": evaluation.latency_seconds, "estimated_cost": evaluation.estimated_cost,
            "metrics": evaluation.metrics, "error": evaluation.error}
        with self._connect() as db:
            db.execute("INSERT INTO evaluations(fingerprint,task_id,score,payload) VALUES (?,?,?,?)",
                (candidate.fingerprint, evaluation.task_id, evaluation.score, json.dumps(payload)))

    def counts(self):
        with self._connect() as db:
            return {"candidates": db.execute("SELECT COUNT(*) FROM candidates").fetchone()[0],
                    "evaluations": db.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]}
