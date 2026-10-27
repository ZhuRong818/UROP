"""Separate attribution from claim type; conservative development diagnostics."""
import re

def classify(evidence,channel):
    text=evidence['quote']
    result={'attributed':bool(re.search(r'\b(?:says?|said|reported|according to)\b',text,re.I)),
            'role':'unresolved','evidence':evidence,'truth_verified':False,'predictive_admitted':False}
    if re.search(r'Most Read from|Related Articles|Recommended Stories',text,re.I):
        return {**result,'role':'contaminated_summary_context'}
    if re.search(r'\b(?:may|might|could|expects?|predicts?|forecasts?|will|would)\b',text,re.I):
        return {**result,'role':'prospective_or_modal_claim'}
    if re.search(r'\b(?:believes?|appears?|best|frontrunner|inappropriate|overvalued|undervalued|warns?)\b',text,re.I):
        return {**result,'role':'evaluative_assessment'}
    if re.search(r'\b(?:resumed|signed|suspended|approved|rejected|completed|announced|have held back|has increased|rose|fell|jumps?)\b',text,re.I):
        return {**result,'role':'reported_action_or_observation'}
    # Reporting verb alone is not evidence of fact, opinion, speaker identity or settlement.
    return result

def assess(relation):
    if relation['status']!='event_channel_candidate':return []
    return [classify(e,relation['channel']) for e in relation['evidence']]
