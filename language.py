# localization.py
import json
from pathlib import Path

class Lang:
	_current_lang = "uz"
	_translations = {}

	@classmethod
	def load(cls, file_path: str = "language_dictionary.json"):
		"""Load translations from JSON file"""
		path = Path(file_path)
		if not path.exists(): raise FileNotFoundError(f"Translation file not found: {file_path}")
		with open(path, "r", encoding="utf-8") as f: cls._translations = json.load(f)

	@classmethod
	def set(cls, lang_code: str):
		"""Switch active language"""
		if lang_code in ["uz", "ru", "en"]: cls._current_lang = lang_code
		else: cls._current_lang = "uz"

	@classmethod
	def use(cls, key: str):
		"""Fetch translation for the active language"""
		entry = cls._translations.get(key, {})
		if not entry: return f"[{key}]"
		if "all" in entry: return entry["all"]
		return entry.get(cls._current_lang, f"[{key}]")
