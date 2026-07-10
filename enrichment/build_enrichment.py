import json, re, os
def _find_root(start):
    d = os.path.dirname(os.path.abspath(start))
    while True:
        if os.path.exists(os.path.join(d, ".atlas-root")): return d
        p = os.path.dirname(d)
        if p == d: return os.path.dirname(os.path.abspath(start))
        d = p
ROOT = _find_root(__file__)

# ---------------- CORPUS EVIDENCE (match substring in sign name -> list of findings) ----------------
# Each finding: p=paper label, f=finding text (source-grounded), y=year
E = {}
def add(key, p, f, pg=None):
    item = {"p": p, "f": f}
    if pg:
        item["pg"] = pg          # source page reference (provenance) when known
    E.setdefault(key, []).append(item)

add("epigastric","Foldvary-Schaefer 2011","Abdominal auras associated with TLE in 74%; rising to 98% when the seizure evolves into an automotor component.")



add("oral automatisms","Loddenkemper 2005","Unilateral automatisms are typically ipsilateral to the epileptogenic zone; strongest when paired with contralateral dystonic posturing.")

add("unilateral manual","Loddenkemper 2005","Unilateral automatisms tend to be ipsilateral to the EZ; the pairing 'ipsilateral automatism + contralateral dystonia' is the classic lateralizing dyad.")
add("unilateral manual","Fakhoury 1994","In R-vs-L TLE, ipsilateral limb automatisms combined with contralateral posturing best separated the groups; contralateral posturing tends to inhibit ipsilateral automatisms.")

add("contralateral dystonic","Loddenkemper 2005","Unilateral dystonic posturing occurs in 43.9% of TLE and is contralateral to the EZ in ~100% (single exception reported by Yen); mechanism = basal-ganglia activation.")
add("contralateral dystonic","Foldvary-Schaefer 2011","Limb dystonia is contralateral to the EZ in >90% of cases.")

add("figure-of-4","Kotagal 2000","In secondarily-generalized seizures the extended elbow was contralateral to onset in 94.4% (extratemporal) and 83–88% (temporal); asymmetric tonic limb posturing present in 75% of TLE and 53% of extratemporal 2°-GTC seizures.")
add("figure-of-4","Loddenkemper 2005","Figure-of-4 present in 17.7% of TLE / 15% of extratemporal epilepsy; extended arm contralateral in 89%.")
add("figure-of-4","Marashly 2015","Caution: in a systematic video-PPV analysis, figure-of-4 and hand dystonia had PPV <80% — less reliable in isolation than version, unilateral tonic posturing, M2e, or unilateral clonic activity.")

add("late forced","Loddenkemper 2005","Forced version present in 22.2% of FLE; contralateral to the EZ in 100% (Brodmann 6/8), especially the pre-GTCS versive turn.")
add("late forced","Roh 1996","Forced version occurred exclusively on the contralateral side in 89% of seizures.")
add("late forced","Foldvary-Schaefer 2011","Head/eye deviation accompanied by true forced version is contralateral to the seizure-onset zone; head rotation without a versive component tends to be ipsilateral — the versive quality, not the turn itself, carries the lateralizing value.")
add("late forced","Wyllie 1986","Foundational series (37 patients, 74 seizures): versive (forced, involuntary, sustained) head/eye deviation was contralateral to the focus in every lateralizing instance — contralateral versive in 61 seizures / 27 patients, with ipsilateral versive never observed — whereas non-versive turning occurred ipsi- and contralaterally with equal frequency and was non-localizing.")

add("early non-forced","Roh 1996","Non-forced head deviation was contralateral in 63% and ipsilateral in 35% — weak and not statistically significant, unlike forced version.")

add("automatism + contralateral","Fakhoury 1994","The ipsilateral-automatism-plus-contralateral-posturing pattern differentiated right from left TLE; contralateral posturing inhibits ipsilateral automatisms.")

add("preserved responsiveness","Loddenkemper 2005","Automatisms with preserved responsiveness occur in 5.7% of TLE and lateralize to the non-dominant hemisphere in ~100% (one exception, Janszky).")
add("preserved responsiveness","Foldvary-Schaefer 2011","Preserved consciousness during automatisms supports a non-dominant temporal origin.")

add("ictal spitting","Loddenkemper 2005","Ictal spitting occurs in ~0.3% of monitored patients; non-dominant in 75%.")

add("ictus emeticus","Loddenkemper 2005","Ictal vomiting in ~2% of monitored patients; non-dominant (right) in 81% (14/16 right-lateralized); non-dominant temporal + Papez circuit.")
add("ictus emeticus","Foldvary-Schaefer 2011","Abdominal aura combined with vomiting further increases the probability of temporal (non-dominant) origin.")

add("eye blinking","Loddenkemper 2005","Unilateral ictal eye-blinking in ~1.5% of monitored patients; ipsilateral to the EZ in 83%.")
add("eye blinking","Roh 1996","Unilateral eye-blinking occurred ipsilateral to ictal EEG onset in 85.7%.")

add("postictal nose","Loddenkemper 2005","Postictal nose-wiping in 53.2% of TLE; the wiping hand is ipsilateral to the EZ in 92%.")

add("postictal aphasia","Gabr 1989","Postictal dysphasia lateralized to the dominant temporal lobe in 92% (p<0.001).")
add("postictal aphasia","Loddenkemper 2005","Postictal dysphasia/aphasia is dominant-hemisphere in 80–100% across series.")
add("postictal aphasia","Serafetinides 1963","Classic n=100 anterior-temporal-lobectomy series establishing dysphasia with dominant-temporal seizure origin.")
add("postictal aphasia","Unterberger 2021","Critical appraisal: 'epileptic aphasia' is heterogeneous — post-ictal aphasia is a robust dominant-hemisphere sign, but ictal language phenomena require careful, structured testing to interpret.")

add("ictal aphasia","Gabr 1989","Ictal dysphasia/aphasia lateralized to the dominant hemisphere in ~100%; ictal preserved (identifiable) speech to the non-dominant side in 83%.")
add("ictal aphasia","Loddenkemper 2005","Ictal speech that is preserved/identifiable is non-dominant in 83%; ictal dysphasia is dominant in 100%.")

add("ictal aphasia / speech arrest","Gabr 1989","Ictal dysphasia dominant ~100%; preserved ictal speech non-dominant 83%.")

add("paraphasia","Gabr 1989","Paraphasic/abnormal ictal speech carries dominant-hemisphere lateralizing value; abnormal speech occurred (ictally or postictally) in 51.4% of patients studied.")
add("paraphasia","Unterberger 2021","Ictal paraphasia is an uncommon but dominant-lateralizing language sign requiring structured ictal testing to capture.")

add("focal clonic","Loddenkemper 2005","Unilateral clonic activity in 44.4% of FLE; contralateral to the EZ in 83% (Brodmann 4/6).")
add("focal clonic","Marashly 2015","Unilateral clonic activity is a 'reliable' motor sign (PPV >80%) for contralateral lateralization.")

add("focal hand/finger clonic","Loddenkemper 2005","Unilateral clonic activity contralateral in 83%; hand representation most common.")

add("todd","Loddenkemper 2005","Postictal (Todd's) palsy in ~0.6% of monitored patients; contralateral to the EZ in 93%.")
add("postictal unilateral limb","Loddenkemper 2005","Postictal paresis is contralateral to the EZ in 93% (Todd's palsy data).")

add("bilateral asymmetric tonic","Loddenkemper 2005","Tonic activity in 48.1% of FLE; the asymmetric (extended) side is contralateral in 89% (SMA / Brodmann 6).")
add("bilateral asymmetric tonic","Marashly 2015","Unilateral tonic posturing is a 'reliable' sign (PPV >80%); two reliable signs pointing the same way give ~100% lateralization accuracy.")

add("somatosensory aura","Loddenkemper 2005","Unilateral sensory aura in 6.1% of patients; contralateral in 89% (Brodmann 1/2/3).")

add("ictal pain","Hwang 2019","Ictal pain occurs in 0.2–2.8% of people with epilepsy (up to 4.1% in focal epilepsy). Somatosensory pain → parietal operculum / insula; abdominal pain → temporal & parietal foci (amygdala/insula). Contralateral when somatotopically organized.")

add("elementary visual","Loddenkemper 2005","Hemifield visual aura in 28.6% of occipital-lobe epilepsy; contralateral hemifield in 100% (Brodmann 17–19).")

add("m2e","Marashly 2015","M2e (mouth-to-hand, Ajmone-Marsan) is a 'reliable' motor sign (PPV >80%) with strong contralateral value — provided the contralateral arm is the one moving to the mouth.")


add("hypermotor","Bonini 2014","French SEEG analysis maps hypermotor behaviour along a rostro-caudal frontal gradient; ventromedial-prefrontal/orbitofrontal onset yields the most distal, integrated hyperkinetic behaviours.")



# ---------------- NEW SIGNS surfaced by the corpus ----------------
NEW = [
  {"region":"Frontal","sub":"Frontal / Precentral Operculum (Brodmann 6 / 44)",
   "sign":"Ictal dysprosody (altered speech melody / prosody)","phase":"Ictal",
   "lat":"Non-dominant hemisphere","latcode":"nondominant",
   "loc":"Non-dominant precentral (frontal) operculum, Brodmann 6/44",
   "sens":"Rare","spec":"High when present","evid":"II",
   "notes":"Recurrent ictal speech utterances with abnormal melody/intonation (dysprosody) rather than aphasic content. Intracranial EEG localizes the discharge to the NON-dominant precentral operculum — the prosodic mirror of dominant-hemisphere language cortex. Helps lateralize to the non-dominant frontal operculum when speech is altered but not aphasic.",
   "cite":"Montavont et al., Epileptic Disord 2005",
   "_ev":[{"p":"Montavont 2005","f":"Ictal recurrent speech with altered prosody corresponded to ictal discharge of the non-dominant precentral operculum, giving dysprosody localizing value to the non-dominant frontal operculum."}]},

  {"region":"Temporal","sub":"Mesial Temporal (Amygdala / Hippocampus / Entorhinal Cortex)",
   "sign":"Ictal central apnea (breathing cessation)","phase":"Ictal",
   "lat":"Non-lateralizing (localizes to mesial temporal)","latcode":"nonlat",
   "loc":"Mesial temporal — amygdala / peri-amygdalar central-apnea network",
   "sens":"~45% for mesial temporal onset","spec":"~82% (0.95 when followed by focal impaired awareness)","evid":"II",
   "notes":"Objective cessation of airflow AND respiratory effort during a focal seizure — distinct from the subjective dyspnea / respiratory-distress aura. Strongly predicts MESIAL TEMPORAL onset: OR 3.8 (specificity 0.82, sensitivity 0.45); when it is followed by focal impaired awareness the odds rise ~30-fold (specificity 0.95). No lateral-temporal or insular onsets showed it. Occurs in ~17.5% of focal seizures / 39% of patients, who have more temporal-lobe onset (85% vs 52%). The amygdala ipsilateral to the epileptogenic zone is enlarged in affected patients (a structural, not lateralizing, correlate). Clinically important as a SUDEP-relevant sign.",
   "cite":"Lacuey et al., Ann Neurol 2024; Meletti et al., Neurology 2025",
   "_ev":[
     {"p":"Lacuey 2024","f":"Ictal central apnea predicted mesial temporal seizure onset (OR 3.8, specificity 0.82, sensitivity 0.45); when followed by focal impaired awareness, specificity rose to 0.95; no lateral-temporal or insular onsets showed it.","pg":"pp.998-1008"},
     {"p":"Meletti 2025","f":"Ictal central apnea in 17.5% of focal seizures / 39% of patients; patients with it had higher temporal-lobe onset than those without (85% vs 52%, p=0.01).","pg":"p.e213856"}
   ]},

  {"region":"Temporal","sub":"Mesial Temporal (Amygdala / Hippocampus / Entorhinal Cortex)",
   "sign":"Postictal central apnea (breathing cessation)","phase":"Postictal",
   "lat":"Non-lateralizing (localizes to mesial temporal / TLE)","latcode":"nonlat",
   "loc":"Mesial temporal; downstream of ictal central apnea; ipsilateral amygdala enlargement",
   "sens":"Rare (~6% of focal seizures)","spec":"High for TLE when present","evid":"II",
   "notes":"Central apnea persisting AFTER seizure end. Occurs in 5.9% of focal seizures and 33.8% of seizures that had ictal central apnea; never observed without a preceding or concurrent ictal central apnea. Associated with temporal-lobe epilepsy and with an enlarged amygdala ipsilateral to the epileptogenic zone. Established mainly as a SUDEP risk marker (longer postictal central apnea → higher hazard of sudden death) rather than a validated lateralizing sign.",
   "cite":"Meletti et al., Neurology 2025; Ochoa-Urrea et al., Lancet 2025",
   "_ev":[
     {"p":"Meletti 2025","f":"Postictal central apnea in 24/406 (5.9%) focal seizures and 24/71 (33.8%) of seizures with ictal central apnea; never without a preceding/concurrent ictal central apnea; associated with TLE and ipsilateral amygdala enlargement.","pg":"p.e213856"},
     {"p":"Ochoa-Urrea 2025","f":"Longer postictal central apnea was a risk marker for sudden unexpected death in epilepsy (hazard ratio 1.32 per 10 s; cutoff >14 s).","pg":"pp.1497-1507"}
   ]},

  {"region":"Temporal","sub":"Mesial Temporal (Amygdala / Hippocampus / Entorhinal Cortex)",
   "sign":"Ictal drinking automatism","phase":"Ictal",
   "lat":"Non-dominant (right) temporal","latcode":"nondominant",
   "loc":"Non-dominant (right) temporal lobe",
   "sens":"Uncommon","spec":"Right-temporal lateralizing when present","evid":"III",
   "notes":"Automatic drinking (reaching for and sipping water) during or just after a focal impaired-awareness seizure, reported as more common with right (non-dominant) temporal foci. Belongs to the cluster of right-temporal autonomic automatisms alongside ictal spitting and vomiting. Corroborative rather than definitive in isolation.",
   "cite":"Abou-Khalil (in Misulis et al. 2022)",
   "_ev":[{"p":"Abou-Khalil (in Misulis et al. 2022)","f":"Spitting and drinking automatisms suggest right temporal localization; ictal spitting, ictal flatulence, and ictal drinking are more common with right temporal foci.","pg":"ch 3.4 pp.41-42"}]},

  {"region":"Temporal","sub":"Mesial Temporal (Amygdala / Hippocampus / Entorhinal Cortex)",
   "sign":"Postictal cough","phase":"Postictal",
   "lat":"Non-dominant (right) temporal","latcode":"nondominant",
   "loc":"Non-dominant (right) temporal lobe",
   "sens":"Uncommon","spec":"Right-temporal lateralizing when present","evid":"III",
   "notes":"Coughing shortly after seizure termination, found predominantly following right (non-dominant) temporal-lobe seizures. One of several right-temporal autonomic/postictal lateralizing signs; not sufficient in isolation but contributes when combined with other signs.",
   "cite":"Abou-Khalil (in Misulis et al. 2022)",
   "_ev":[{"p":"Abou-Khalil (in Misulis et al. 2022)","f":"Post-ictal cough has been found predominantly following right temporal seizures.","pg":"ch 3.4 p.42"}]},

  {"region":"Temporal","sub":"Mesial Temporal (Amygdala / Hippocampus / Entorhinal Cortex)",
   "sign":"Postictal urinary urgency","phase":"Postictal",
   "lat":"Non-dominant (right) temporal","latcode":"nondominant",
   "loc":"Non-dominant (right) temporal lobe",
   "sens":"Uncommon","spec":"Right-temporal lateralizing when present","evid":"III",
   "notes":"An urge to urinate after a seizure, suggesting a right (non-dominant) temporal localization. A right-temporal autonomic lateralizing sign; corroborative, to be weighed together with other signs rather than used alone.",
   "cite":"Abou-Khalil (in Misulis et al. 2022)",
   "_ev":[{"p":"Abou-Khalil (in Misulis et al. 2022)","f":"Post-ictal urinary urgency suggests a right temporal localization.","pg":"ch 3.4 p.42"}]},
]

# ---------------- PAPER LIBRARY (deduplicated) ----------------
PAPERS = [
 ("Loddenkemper & Kotagal 2005","Epilepsy & Behavior","Lateralizing signs during seizures in focal epilepsy","Comprehensive lateralizing-sign review; source of the frequency + lateralization-% table used throughout."),
 ("Foldvary-Schaefer & Unnwongse 2011","Epilepsy & Behavior","Localizing and lateralizing features of auras and seizures","Aura/seizure localization review; abdominal-aura → TLE probabilities and motor-sign lateralization."),
 ("Marashly et al. 2015","Epilepsia","Ictal motor sequences: lateralization and localization values","PPV-based ranking of motor signs and the sequence rule (≥2 reliable signs → ~100% accuracy)."),
 ("Kotagal et al. 2000","Epilepsia","Lateralizing value of asymmetric tonic limb posturing in secondarily generalized seizures","Figure-of-4 / ATLP quantification: extended elbow contralateral in up to 94%."),
 ("Kotagal & Lay 2018","Seizure","Lateralizing / localizing value of seizure semiology (update)","Contemporary synthesis of semiological lateralizing signs."),
 ("Gabr et al. 1989","Annals of Neurology","Speech manifestations in lateralization of temporal lobe seizures","Postictal dysphasia → dominant 92%; preserved ictal speech → non-dominant 83%."),
 ("Serafetinides & Falconer 1963","Brain","Speech disturbances in temporal lobe seizures (n=100 ATL)","Classic large series linking ictal dysphasia to the dominant temporal lobe."),
 ("Montavont et al. 2005","Epileptic Disorders","Ictal dysprosody and the non-dominant frontal operculum","Establishes dysprosody as a non-dominant frontal-opercular sign."),
 ("Unterberger et al. 2021","Epilepsy & Behavior","Epileptic aphasia — a critical appraisal","Critical synthesis of ictal/postictal language phenomena and their localizing limits."),
 ("Fakhoury et al. 1994","Epilepsia","Differentiating clinical features of right and left temporal lobe seizures","R-vs-L TLE semiology; automatism–posturing dyad."),
 ("Roh et al. 1996","(Journal of Korean Neurology)","Lateralizing value of ictal behaviors in temporal lobe epilepsy","Version contralateral 89%; eye-blink & unilateral automatism ipsilateral ~85%."),
 ("Bonini et al. 2014","Epilepsia","Frontal lobe seizures: from clinical semiology to localization","French SEEG cohort mapping frontal semiology along a rostro-caudal gradient."),
 ("Khoo et al. 2023","Seizure","Value of semiology in predicting EZ and outcome in frontal lobe surgery","Semiology's predictive value for the frontal EZ and surgical outcome."),
 ("Chauvel & McGonigal 2014","Epilepsy & Behavior","Emergence of semiology in epileptic seizures","Network/dynamic framework: semiology reflects dynamic network interaction, not propagation alone."),
 ("McGonigal et al. 2021","Epilepsia","On seizure semiology","Conceptual framework linking semiology to organized brain networks."),
 ("McGonigal 2022","Journal of Neurology","Frontal lobe seizures: overview and update","Modern overview of frontal-lobe seizure semiology and SEEG correlation."),
 ("Bartolomei / Isnard et al. 2018","Clinical Neurophysiology","French guidelines on SEEG","Methodological standard for stereo-EEG-based anatomo-electro-clinical correlation."),
 ("Maillard et al. 2004","Epilepsia","Semiologic and electrophysiologic correlations in temporal lobe seizure subtypes","SEEG-defined mesial/lateral/mesiolateral temporal subtypes and their semiology."),
 ("Lüders et al. 1998","Epilepsia","Semiological seizure classification","The symptom-based (semiological) seizure classification framework."),
 ("Hwang et al. 2019","Current Pain & Headache Reports","Painful seizures: a review of epileptic ictal pain","Prevalence and network basis of ictal pain (parietal operculum / insula)."),
 ("Kinney, Kovac & Diehl 2019","Seizure","Structured testing during seizures: a practical guide","European consensus ictal–postictal testing battery (how to elicit/verify each sign)."),
 ("Jonas et al. 2016","Frontiers in Human Neuroscience","Language mapping using stereo-EEG","SEEG language-mapping methods relevant to ictal language signs."),
 ("Gibbs et al. 2019","Epilepsia","Clinical features of sleep-related hypermotor epilepsy vs seizure-onset zone","Semiology of SHE in relation to onset zone."),
 ("Suzuki et al. 2017","NMC Case Report Journal","Sensorimotor networks in reflex seizures","Reflex/sensorimotor-network contribution to seizure generation."),
 ("Blair 2012","Epilepsy Research & Treatment","Temporal lobe epilepsy semiology","Focused review of TLE semiology."),
 ("Sisodiya 2004","Lancet Neurology","Malformations of cortical development and epilepsy","Structural substrate context for focal epilepsy."),
 ("Jain et al. 2021","J Neurosurg Pediatrics","Bottom-of-sulcus dysplasia resection (pediatric)","Lesional/EZ concordance in focal dysplasia (pediatric context)."),
 ("Hauser 1993","Epilepsia","Epidemiology of epilepsy","Population context for focal epilepsy syndromes."),
 ("Chowdhury & Walker (Localisation practical guide)","Practical Neurology","Localisation in focal epilepsy: a practical guide","Bedside synthesis of localizing/lateralizing semiology."),
 ("Kotagal (Ictal Speech & Cerebral Dominance)","(monograph excerpt)","Ictal speech disturbance and cerebral dominance","Speech-dominance correlation reference."),
 ("(Ictal paraphasia case study)","Neurocase","Ictal paraphasia as an atypical TLE manifestation","Illustrative dominant-temporal ictal language disturbance."),
 ("Wyllie et al. 1986","Neurology","The lateralizing significance of versive head and eye movements during epileptic seizures","Foundational series: versive (forced, sustained) head/eye deviation is reliably contralateral; non-versive turning is non-localizing."),
 ("Lacuey et al. 2024","Annals of Neurology","Ictal central apnea is predictive of mesial temporal seizure onsets","Intracranial study: ictal central apnea predicts mesial temporal onset (OR 3.8, spec 0.82)."),
 ("Meletti et al. 2025","Neurology","Persistent postictal central apnea in focal seizures: incidence, features, and imaging findings","Postictal central apnea incidence/features; TLE association and ipsilateral amygdala enlargement."),
 ("Ochoa-Urrea et al. 2025","Lancet","Risk markers for sudden unexpected death in epilepsy: an observational, prospective, multicentre cohort study","SUDEP cohort: ictal/postictal central-apnea duration as mortality risk markers."),
 ("Abou-Khalil (in Misulis et al. 2022)","Oxford Univ. Press","Atlas of EEG, Seizure Semiology, and Management, 3rd ed. — Seizure semiology by localization (ch 3.4)","Authoritative textbook chapter corroborating the lateralizing direction of version, dystonic/tonic/clonic posturing, figure-of-4, somatosensory, spitting, vomiting, preserved-responsiveness automatisms, eye-blinking, nose-wiping and postictal aphasia."),
]

# ---------------- LATERALIZATION RELIABILITY DATA ----------------
# Single-source, primary-literature: Loddenkemper & Kotagal 2005 (Epilepsy & Behavior), Table 1.
# pct = % of cases lateralizing in the stated direction; freq = reported frequency in the cited population.
# dir uses the resource's existing latcode palette: contra / ipsi / dominant / nondominant.
LATERAL = [
 # ---- Contralateral ----
 {"sign":"Forced version (pre-GTC)","dir":"contra","pct":100,"freq":"22.2% of FLE"},
 {"sign":"Unilateral dystonic posturing","dir":"contra","pct":100,"freq":"43.9% of TLE"},
 {"sign":"Hemifield visual aura","dir":"contra","pct":100,"freq":"28.6% of OLE"},
 {"sign":"Postictal (Todd's) palsy","dir":"contra","pct":93,"freq":"0.6% of EMU pts"},
 {"sign":"Tonic activity (asymmetric)","dir":"contra","pct":89,"freq":"48.1% of FLE"},
 {"sign":"Figure-of-4 (extended arm)","dir":"contra","pct":89,"freq":"17.7% of TLE"},
 {"sign":"Unilateral sensory aura","dir":"contra","pct":89,"freq":"6.1% of pts"},
 {"sign":"Unilateral clonic activity","dir":"contra","pct":83,"freq":"44.4% of FLE"},
 # ---- Ipsilateral ----
 {"sign":"Postictal nose-wiping","dir":"ipsi","pct":92,"freq":"53.2% of TLE"},
 {"sign":"Unilateral eye-blinking","dir":"ipsi","pct":83,"freq":"1.5% of EMU pts"},
 # ---- Dominant hemisphere ----
 {"sign":"Ictal dysphasia / aphasia","dir":"dominant","pct":100,"freq":"34.2% of EMU pts"},
 # ---- Non-dominant hemisphere ----
 {"sign":"Automatisms w/ preserved responsiveness","dir":"nondominant","pct":100,"freq":"5.7% of TLE"},
 {"sign":"Ictal speech (preserved/identifiable)","dir":"nondominant","pct":83,"freq":"34.2% of EMU pts"},
 {"sign":"Ictal vomiting","dir":"nondominant","pct":81,"freq":"2% of EMU pts"},
 {"sign":"Ictal spitting","dir":"nondominant","pct":75,"freq":"0.3% of EMU pts"},
]

# ---------------- INTAKE FINDINGS (page-cited) ----------------
# Page-referenced findings from intake live in intake_findings.json, kept separate
# from the hand-authored evidence above so provenance stays auditable;
# tools/check_provenance.py gates every entry (each must carry a source page).
_intake_path = os.path.join(ROOT, "enrichment", "intake_findings.json")
if os.path.exists(_intake_path):
    with open(_intake_path) as _f:
        _intake = json.load(_f)
    _known = {p[0] for p in PAPERS}
    for _pap in _intake.get("papers", []):
        _cite = _pap.get("cite")
        if _cite and _cite not in _known:
            PAPERS.append((_cite, _pap.get("journal", ""), _pap.get("title", ""), _pap.get("contribution", "")))
            _known.add(_cite)
    # New signs proposed by intake (a paper presenting a sign not yet in the atlas).
    # They are added just like the hand-authored NEW signs above and get an id at
    # build time; findings can then attach to them.
    _newnames = {n["sign"].lower() for n in NEW}
    for _ns in _intake.get("new_signs", []):
        if _ns.get("sign") and _ns["sign"].lower() not in _newnames:
            NEW.append(_ns)
            _newnames.add(_ns["sign"].lower())
    for _fnd in _intake.get("findings", []):
        add(_fnd["sign_stem"], _fnd["paper"], _fnd["finding"], _fnd.get("pg"))

out = {"evidence":E,"new_signs":NEW,"papers":PAPERS,"lateral":LATERAL}
json.dump(out, open(os.path.join(ROOT,"enrichment","enrichment.json"),"w"), indent=1)
print("Evidence keys:",len(E)," New signs:",len(NEW)," Papers:",len(PAPERS)," Lateral rows:",len(LATERAL))
print("Total evidence findings:", sum(len(v) for v in E.values()))