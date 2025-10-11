import json
import math
from typing import Dict, Tuple, List, Any, Optional, NamedTuple

ROMAN = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
    "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20,
    "XXI": 21, "XXII": 22, "XXIII": 23, "XXIV": 24, "XXV": 25
}

LH_CATEGORIES = {
    "LH", "EC", "EN", "IC", "ICN", "EXP", "NCL", "ES*", "FR", "FA", "FB", "NTV"
}

class TrackMetadata(NamedTuple):
    num: Optional[int]
    suffix: str
    len_compl: int
    cap_fun: int

class CandidateRank(NamedTuple):
    name: str
    priority_class: int
    proximity: float
    neg_similarity: int
    same_number_bonus: int
    len_delta: int
    sort_num: float
    suffix_flag: int

def is_lh(t: Optional[str]) -> bool:
    """Restituisce True se t (train type) è una classe di lunga percorrenza."""
    tt = (t or "").upper().strip()
    return tt in LH_CATEGORIES

def parse_track_name(name: str) -> Tuple[Optional[int], str, str]:
    """
    Restituisce (numero, suffisso, nome_normalizzato):
    - numero: int (o None) estratto dal nome (cifra o numero romano)
    - suffisso: seconda parte se presente (es. 'BIS'), altrimenti stringa vuota
    - nome_normalizzato: nome del binario in maiuscolo senza spazi ridondanti
    """
    if not isinstance(name, str):
        return None, "", ""
    norm = " ".join(name.strip().upper().split())
    if not norm:
        return None, "", ""
    parts = norm.split()
    first = parts[0]
    
    num = int(first) if first.isdigit() else ROMAN.get(first)
    suffix = parts[1] if len(parts) > 1 else ""
    return num, suffix, norm

def class_matches_ES_star(train_type: str) -> bool:
    """True per classe 'ES' o 'ES*'."""
    tt = (train_type or "").upper().strip()
    return tt in ("ES", "ES*")

def profile_tuple(info: Dict[str, Any]) -> Tuple[int, int]:
    """
    Rappresenta il profilo del marciapiede:
    (a = 1 se esiste marciapiede alto, b = 1 se esiste marciapiede basso).
    """
    a = 1 if (info.get("marciapiede_alto_m") or 0) > 0 else 0
    b = 1 if (info.get("marciapiede_basso_m") or 0) > 0 else 0
    return (a, b)

def track_similarity_score(cand_info: Dict[str, Any], 
                           planned_info: Optional[Dict[str, Any]]) -> int:
    """
    Punteggio di somiglianza con il binario previsto:
      +2 se 'marciapiede_complessivo_m' coincide (>0)
      +1 se il profilo (alto/basso) coincide
    """
    if not planned_info:
        return 0
    score = 0
    c_mc = cand_info.get("marciapiede_complessivo_m") or 0
    p_mc = planned_info.get("marciapiede_complessivo_m") or 0
    if c_mc > 0 and c_mc == p_mc:
        score += 2
    if profile_tuple(cand_info) == profile_tuple(planned_info):
        score += 1
    return score

def priority_class(train_type: str, num: Optional[int]) -> int:
    """
    0 = migliore, 1 = peggiore
    (Per LH: binari da 2 a 13 priorità 0; 1 e 14 priorità 1; altri esclusi)
    """
    if is_lh(train_type) and isinstance(num, int):
        return 0 if 2 <= num <= 13 else 1
    return 0

def proximity_rank(candidate_num: Optional[int], candidate_suffix: str,
                   planned_num: Optional[int], planned_suffix: str) -> float:
    """
    Distanza di prossimità tra binari:
      - 1 se 'gemello' del previsto (stesso numero, suffisso diverso, es. V vs V BIS)
      - |num - planned_num| altrimenti (diferenza assoluta)
      - math.inf se uno dei numeri è sconosciuto
    """
    if candidate_num is None or planned_num is None:
        return math.inf
    if candidate_num == planned_num and candidate_suffix != planned_suffix:
        return 1
    return abs(candidate_num - planned_num)

def validate_track_data(track_name: str, info: Dict[str, Any]) -> bool:
    """Valida che un binario abbia i campi obbligatori con valori validi"""
    required_fields = ["marciapiede_complessivo_m"]
    for field in required_fields:
        value = info.get(field)
        if value is None:
            print(f"WARNING: Binario '{track_name}' manca il campo '{field}'. Verrà ignorato.")
            return False
        try:
            int(value)
        except (ValueError, TypeError):
            print(f"WARNING: Binario '{track_name}' ha valore non numerico in '{field}': {value}")
            return False
    return True

def build_track_metadata(tracks: Dict[str, Dict[str, Any]]) -> Dict[str, TrackMetadata]:
    """Costruisce i metadati dei binari con validazione"""
    track_meta: Dict[str, TrackMetadata] = {}
    for name, info in tracks.items():
        if not validate_track_data(name, info):
            continue
        num, suffix, norm = parse_track_name(name)
        len_compl = int(info.get("marciapiede_complessivo_m") or 0)
        cap_fun = int(info.get("capacita_funzionle_m") or 0)
        track_meta[norm] = TrackMetadata(num, suffix, len_compl, cap_fun)
    return track_meta

def resolve_planned_track(planned_track: Optional[str], 
                         track_meta: Dict[str, TrackMetadata],
                         tracks: Dict[str, Dict[str, Any]]) -> Tuple[Optional[int], str, Optional[Dict[str, Any]]]:
    """Risolve il binario previsto con gestione errori"""
    if not planned_track:
        return None, "", None
    
    p_num, p_suffix, p_norm = parse_track_name(planned_track)
    planned_num = p_num
    planned_suffix = p_suffix or ""
    
    num_suffix_to_norm = {
        (meta.num, meta.suffix): norm_name 
        for norm_name, meta in track_meta.items()
    }
    
    resolved_norm = num_suffix_to_norm.get((planned_num, planned_suffix))
    if not resolved_norm:
        resolved_norm = p_norm
    
    planned_info = tracks.get(resolved_norm)
    
    if not planned_info and planned_track:
        print(f"WARNING: Binario previsto '{planned_track}' non trovato nei dati. Prossimità disabilitata.")
    
    return planned_num, planned_suffix, planned_info

def is_track_excluded(norm_name: str, num: Optional[int], suffix: str,
                     train_type: str, is_inv: bool,
                     planned_num: Optional[int], planned_suffix: str) -> bool:
    """Verifica se un binario deve essere escluso in base alle regole"""
    if planned_num is not None and num == planned_num and suffix == planned_suffix:
        return True
    
    is_bis = (suffix == "BIS")
    if is_bis and not is_inv:
        return True
    
    if train_type == "PRM" and (norm_name == "I NORD" or (num == 1 and " NORD" in norm_name)):
        return True
    
    if class_matches_ES_star(train_type) and num == 15:
        return True
    
    if is_lh(train_type):
        if not (isinstance(num, int) and 1 <= num <= 14):
            return True
    
    return False

def meets_length_requirements(len_compl: int, cap_fun: int, 
                              train_length: int, is_inv: bool) -> bool:
    """Verifica se un binario soddisfa i requisiti di lunghezza"""
    if not is_inv and len_compl <= 0:
        return False
    
    if is_inv:
        if cap_fun > 0:
            return cap_fun >= train_length
        else:
            return len_compl == 0 or len_compl >= train_length
    else:
        return len_compl >= train_length

def calculate_ranking_criteria(norm_name: str, num: Optional[int], suffix: str,
                               train_type: str, planned_num: Optional[int], 
                               planned_suffix: str, planned_info: Optional[Dict[str, Any]],
                               tracks: Dict[str, Dict[str, Any]], 
                               len_compl: int) -> CandidateRank:
    """Calcola tutti i criteri di ordinamento per un candidato"""
    prox = proximity_rank(num, suffix, planned_num, planned_suffix)
    cand_info = tracks.get(norm_name, {})
    sim = track_similarity_score(cand_info, planned_info)
    planned_len = int(planned_info.get("marciapiede_complessivo_m") or 0) if planned_info else 0
    len_delta = abs((planned_len or len_compl) - len_compl)
    pclass = priority_class(train_type, num)
    sort_num = float(num) if isinstance(num, int) else math.inf
    suffix_flag = 1 if suffix else 0
    same_number_bonus = -1 if (planned_num is not None and num == planned_num and suffix != planned_suffix) else 0
    
    return CandidateRank(
        name=norm_name,
        priority_class=pclass,
        proximity=prox,
        neg_similarity=-sim,
        same_number_bonus=same_number_bonus,
        len_delta=len_delta,
        sort_num=sort_num,
        suffix_flag=suffix_flag
    )

def scegli_per_un_treno(
    train_code: str,
    train_len: int,
    train_type_in: str,
    tracks: Dict[str, Dict[str, Any]],
    planned_track: Optional[str] = None
) -> List[str]:
    """
    Applica regole e ritorna fino a 7 binari alternativi per un treno
    """
    train_type = (train_type_in or "").upper().strip()
    is_inv = (train_type == "INV")
    
    try:
        train_length = int(train_len)
        if train_length <= 0:
            raise ValueError("La lunghezza deve essere maggiore di 0")
    except (ValueError, TypeError) as e:
        print(f"ERRORE: Lunghezza treno non valida '{train_len}': {e}")
        return []
    
    track_meta = build_track_metadata(tracks)
    
    if not track_meta:
        print("ERRORE: Nessun binario valido trovato nei dati.")
        return []
    
    planned_num, planned_suffix, planned_info = resolve_planned_track(
        planned_track, track_meta, tracks
    )
    
    candidates: List[CandidateRank] = []
    
    for norm_name, meta in track_meta.items():
        if is_track_excluded(norm_name, meta.num, meta.suffix, train_type, 
                           is_inv, planned_num, planned_suffix):
            continue
        
        if not meets_length_requirements(meta.len_compl, meta.cap_fun, 
                                        train_length, is_inv):
            continue
        
        rank = calculate_ranking_criteria(
            norm_name, meta.num, meta.suffix, train_type,
            planned_num, planned_suffix, planned_info, tracks, meta.len_compl
        )
        candidates.append(rank)
    
    candidates.sort(key=lambda x: (
        x.priority_class, x.proximity, x.neg_similarity, 
        x.same_number_bonus, x.len_delta, x.sort_num, x.suffix_flag
    ))
    
    return [c.name for c in candidates[:7]]

def ask_int(prompt: str) -> int:
    """Richiede un intero > 0 all'utente"""
    while True:
        s = input(prompt).strip()
        try:
            v = int(s)
            if v > 0:
                return v
        except ValueError:
            pass
        print("Valore non valido. Inserisci un intero > 0.")

def ask_str(prompt: str, default: Optional[str] = None) -> str:
    """Richiede una stringa all'utente, restituendo il default se fornito"""
    s = input(prompt).strip()
    return s if s else (default or "")

def validate_json_data(data: Dict[str, Any]) -> bool:
    """Valida la struttura del file JSON"""
    if "binari" not in data:
        print("ERRORE: Il file 'dati.json' deve contenere la chiave 'binari'.")
        return False
    
    if not isinstance(data["binari"], dict):
        print("ERRORE: 'binari' deve essere un oggetto JSON.")
        return False
    
    if not data["binari"]:
        print("ERRORE: Nessun binario definito in 'dati.json'.")
        return False
    
    return True

if __name__ == "__main__":
    try:
        with open("dati.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Errore: file 'dati.json' non trovato.")
        exit(1)
    except json.JSONDecodeError as e:
        try:
            with open("dati.json", "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"Errore: il file 'dati.json' contiene JSON non valido: {e}")
            exit(1)
    
    if not validate_json_data(data):
        exit(1)
    
    binari: Dict[str, Dict[str, Any]] = data.get("binari", {})
    
    train_code = input("Inserisci NUMERO TRENO: ").strip()
    train_len = ask_int("Inserisci LUNGHEZZA treno (m): ")
    base_cls = ask_str("Inserisci CLASSE treno (es. REG, IC, ES*, INV...) [default REG]: ", default="REG").upper()
    
    prm_flag = input("È un treno PRM? [s/N]: ").strip().lower()
    is_prm = prm_flag in ("s", "si", "y", "yes", "1")
    
    planned_input = ask_str("Binario previsto (es. 'V', '10', 'I NORD') [Invio per saltare]: ")
    planned = planned_input if planned_input else None
    
    train_type = "PRM" if is_prm else base_cls
    
    alternatives = scegli_per_un_treno(train_code, train_len, train_type, binari, planned)
    
    print(f"\nTreno {train_code} (len={train_len}, cls={train_type})")
    if planned:
        print(f"Binario previsto: {planned}")
    if alternatives:
        print("Alternative (in ordine di priorità):")
        for i, b in enumerate(alternatives, start=1):
            print(f"{i}. {b}")
    else:
        print("Nessun binario alternativo compatibile trovato.")
    
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump({train_code: alternatives}, f, ensure_ascii=False, indent=2)
    print("\nOK: scritto output.json")
