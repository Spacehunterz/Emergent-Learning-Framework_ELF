# Prior Art Research: Intelligent Heuristic Systems
## Phase 2 Ultrathink Research Report

**Agent:** 5 (Research Specialist)
**Date:** 2025-12-12
**Mission:** Investigate existing systems for confidence scoring, fraud detection, and heuristic management

---

## Executive Summary

After comprehensive research across expert systems, reputation platforms, anomaly detection algorithms, trust metrics, knowledge graphs, and machine learning approaches, several key insights emerge for our Emergent Learning Framework (ELF):

### Critical Insights for ELF

1. **Confidence Scoring**: Dempster-Shafer theory provides superior uncertainty modeling compared to simple probabilities, handling ignorance explicitly and combining evidence from multiple sources.

2. **Fraud Detection**: Multi-layered approaches work best - combining rate-based detection (ADWIN), pattern analysis (isolation forests), and diminishing returns on score accumulation.

3. **Smoothing**: Exponentially Weighted Moving Averages (EWMA) offer optimal balance between responsiveness and stability, with recursive computation requiring minimal storage.

4. **Drift Detection**: ADWIN (Adaptive Windowing) consistently outperforms DDM/EDDM for detecting both gradual and abrupt changes in heuristic effectiveness.

5. **Gaming Prevention**: Reputation systems converge on similar strategies: vote fuzzing, diminishing returns, temporal decay, and context-aware weighting.

6. **Meta-Learning**: Reinforcement learning (especially multi-armed bandits) provides frameworks for exploration/exploitation trade-offs in heuristic selection.

### Recommended Architectural Approach

**Hybrid System**: Combine Dempster-Shafer confidence modeling with EWMA smoothing, ADWIN drift detection, and multi-armed bandit heuristic selection. This creates a self-tuning system that learns which heuristics work in which contexts while detecting and preventing manipulation.

---

## 1. Expert Systems & Knowledge Bases

### 1.1 MYCIN and Certainty Factors

**What it solves**: Medical diagnosis under uncertainty with incomplete information.

**How confidence works**:
- MYCIN uses Certainty Factors (CF) ranging from -1 (definitely false) to +1 (definitely true)
- CF = 0 represents complete ignorance (distinct from 50% probability)
- Combination rule: `CF(A and B) = min(CF(A), CF(B))`
- Parallel evidence: `CF_combined = CF1 + CF2 - (CF1 * CF2)` when both positive

**Anti-gaming mechanisms**: None explicitly - designed for expert input, not crowd-sourced data.

**Applicability to ELF**:
- ✅ The distinction between "unknown" and "50% confident" is valuable
- ❌ Assumes expert-curated rules, not emergent discovery
- ⚠️ Combination rules may be too simplistic for conflicting heuristics

**Source**: [Dempster-Shafer Theory](https://www.shortliffe.net/Buchanan-Shortliffe-1984/Chapter-13.pdf)

---

### 1.2 Dempster-Shafer Theory of Evidence

**What it solves**: Reasoning with uncertainty when evidence points to sets of hypotheses rather than single outcomes.

**How confidence works**:
- **Belief mass**: Assign probability mass to sets of hypotheses, not just single hypotheses
- **Belief function Bel(A)**: Sum of masses of all subsets of A
- **Plausibility Pl(A)**: 1 - Bel(not A) - represents how much evidence doesn't contradict A
- **Dempster's combination rule**: Combines evidence from independent sources, normalizing to remove conflict

**Key advantage over Bayesian**: Can explicitly model ignorance. If you have no evidence about A, you assign mass to the frame of discernment (the set of all possibilities), not 50% to each outcome.

**Handling contradictions**:
- Dempster's rule computes a "conflict coefficient" K
- K = sum of products of conflicting belief masses
- If K approaches 1, evidence is highly contradictory - signals potential fraud or context shift
- Some extensions reject combination when K exceeds threshold

**Applicability to ELF**:
- ✅ **HIGHLY RELEVANT**: Perfect for heuristics that apply to domains, not specific tasks
- ✅ Conflict detection (high K value) can identify fraudulent heuristics or context boundaries
- ✅ Handles "this heuristic works for {frontend, testing}" without forcing probability to specific tasks
- ⚠️ Computational complexity increases with number of hypotheses

**Source**: [The Dempster-Shafer Theory of Evidence](https://www.researchgate.net/publication/242392452_The_Dempster-Shafer_theory_of_evidence)

---

### 1.3 Bayesian Belief Networks

**What it solves**: Probabilistic reasoning with complex dependencies between variables.

**How confidence works**:
- Directed acyclic graph (DAG) where nodes = variables, edges = dependencies
- Conditional probability tables (CPTs) at each node
- Inference propagates probabilities through the network
- Pearl's message-passing algorithm efficiently computes marginal probabilities

**Handling contradictions**:
- Networks can model conflicting evidence by examining posterior probabilities
- Inconsistent evidence typically results in low-probability outcomes
- Sensitivity analysis reveals which evidence contradicts the model

**Modern applications (2024)**:
- Dynamic Bayesian Networks (DBNs) for time-series prediction
- Combined with deep learning for uncertainty quantification
- NeurIPS 2024 workshop focused on Bayesian decision-making under uncertainty

**Applicability to ELF**:
- ✅ Could model dependencies between heuristics (e.g., "use git hooks" depends on "setup is automated")
- ❌ Requires specifying DAG structure upfront - poor fit for emergent discovery
- ⚠️ Computationally expensive for large networks
- 💡 **Potential**: Use for meta-level reasoning about heuristic relationships

**Sources**:
- [Bayesian Networks for Expert Systems](https://link.springer.com/chapter/10.1007/978-3-642-11688-9_20)
- [NeurIPS 2024 Bayesian Decision-making Workshop](https://gp-seminar-series.github.io/neurips-2024/)

---

## 2. Reputation Systems

### 2.1 eBay Reputation System

**What it solves**: Trust establishment between strangers in marketplace transactions.

**How confidence works**:
- Simple feedback: positive (+1), neutral (0), negative (-1) after each transaction
- Total reputation = sum of feedback over time
- Percentage scores (% positive in last 12 months)
- Seller ratings on detailed metrics (accuracy, communication, shipping speed)

**Anti-gaming mechanisms**:
1. **Mutual dependency**: Both parties can leave feedback, deterring retaliation
2. **Time windows**: Recent feedback weighted more heavily
3. **Verification**: Only verified transactions can receive feedback
4. **AI pattern detection**: Neural networks identify voting rings and shill bidding
5. **Human review**: Flagged accounts reviewed by moderators

**Known failures**:
- **Voting rings**: Groups coordinate to upvote each other
- **Retaliation suppression**: Sellers pressure buyers for positive feedback
- **Simplistic model**: Binary positive/negative loses nuance
- **Identity obscurity**: Hard to track repeat offenders across accounts

**2024 innovations**:
- Acquired 3PM Shield (AI fraud detection company)
- Real-time pattern analysis on bidding behavior
- Risk scoring based on user behavior and payment patterns

**Applicability to ELF**:
- ✅ Time decay (recent evidence matters more)
- ✅ Multi-dimensional scoring (not just "good/bad" but context-specific)
- ✅ Verification (only applied heuristics get feedback)
- ❌ eBay struggles with sophisticated fraud - we need better detection

**Sources**:
- [Inside eBay's Real-Time Auction System](https://www.frugaltesting.com/blog/inside-ebays-real-time-auction-system-bidding-logic-algorithms-fraud-prevention-techniques)
- [eBay Acquires 3PM Shield](https://www.retaildive.com/news/ebay-acquires-3pm-shield-artificial-intelligence-fraud-detection/642699/)
- [Fraud Detection at eBay (2025)](https://www.sciencedirect.com/science/article/pii/S1566014125000263)

---

### 2.2 Stack Overflow Reputation System

**What it solves**: Incentivize quality contributions in technical knowledge sharing.

**How confidence works**:
- **Upvote on answer**: +10 reputation
- **Accepted answer**: +15 reputation
- **Upvote on question**: +5 reputation
- **Downvote given**: -1 reputation (cost to discourage casual downvoting)
- **Downvote received**: -2 reputation
- **Badges**: Achievements for specific behaviors (e.g., "Reversal" - answer score 20+ on question score -5 or lower)

**Anti-gaming mechanisms identified in 2024 research**:
1. **Voting ring detection**: Algorithm identifies isolated/semi-isolated communities with circular voting
2. **Vote reversal**: System detects and removes suspicious voting patterns
3. **User removal**: Fraudulent accounts deleted, all reputation reversed
4. **Badge retirement**: Removed badges that encouraged gaming (e.g., "Tumbleweed" for zero-engagement questions)
5. **Edit point limits**: Editing gives minimal reputation to prevent gaming through trivial edits

**Gaming scenarios documented**:
- **Voting rings**: Coordinated groups upvote each other's content
- **Sock puppets**: Multiple accounts controlled by one person
- **Badge hunting**: Optimizing for badge criteria rather than genuine contribution
- **Bounty fraud**: Posting bounties to transfer reputation between accounts (low impact, removed from concern)

**2024 research findings**:
- New users don't understand the gamification system
- Reputation alone loses appeal over time for experts
- Stack Overflow researching more inclusive, engaging reward systems

**Applicability to ELF**:
- ✅ **Cost for negative feedback**: Discourages frivolous challenges to heuristics
- ✅ **Community detection algorithms**: Identify circular validation
- ✅ **Automatic anomaly detection**: Flag suspicious patterns for review
- ⚠️ Distinction between "gaming" and "optimization" is blurry
- 💡 **Key insight**: Simple systems invite gaming; complexity provides defense

**Sources**:
- [Reputation Gaming in Stack Overflow (2024)](https://dl.acm.org/doi/10.1145/3691627)
- [Stack Overflow Research Roadmap (Nov 2024)](https://stackoverflow.blog/2024/11/04/research-roadmap-update-november-2024/)

---

### 2.3 Reddit Karma System

**What it solves**: Content quality filtering and community trust in massive-scale discussions.

**How confidence works**:
- **Post karma**: Accumulated upvotes on submissions
- **Comment karma**: Accumulated upvotes on comments
- **Total karma**: Visible on profile, used for access thresholds
- **Subreddit-specific**: Some communities require minimum karma to post

**Anti-gaming mechanisms**:
1. **Vote fuzzing**: Displayed vote counts include random noise (±500 on popular posts)
   - Makes it impossible to verify manipulation impact
   - Reduces motivation for voting rings
   - Intensity scales with post popularity

2. **Algorithm obscurity**: Vote-to-karma conversion is proprietary and non-linear
   - Prevents reverse-engineering optimal gaming strategies

3. **Diminishing returns**: Each additional upvote contributes less karma
   - Prevents single viral post from disproportionate inflation

4. **Low-karma vote weighting**: New/low-reputation accounts have reduced vote weight
   - Limits bot farm effectiveness

5. **Temporal dynamics**: Old posts contribute to karma but stop accumulating
   - 6-month archive window prevents continuous farming

6. **Account age + karma thresholds**: Many subreddits require BOTH criteria
   - Prevents ban evasion through fresh accounts

**2024-2025 changes**:
- Increasing spam led to stricter thresholds (50-100 karma + 30-day age)
- Subreddits implementing custom AutoModerator rules
- Greater emphasis on account history, not just karma number

**Applicability to ELF**:
- ✅ **Vote fuzzing**: Add noise to displayed confidence scores to deter manipulation
- ✅ **Diminishing returns**: Limit how much a single validation event can boost confidence
- ✅ **Algorithm obscurity**: Don't publish exact scoring formulas
- ✅ **Compound requirements**: Time + validations, not just validations
- ⚠️ Over-obfuscation reduces transparency and trust

**Sources**:
- [Reddit Karma Explained](https://karmatic.ai/how-does-reddit-karma-work-a-complete-guide-for-new-and-experienced-redditors/)
- [What is Reddit's Voting System?](https://dicloak.com/blog-detail/what-is-reddits-voting-system-heres-how-it-works)
- [Reddit Upvotes & Comment Karma (2025 Guide)](https://mediagrowth.io/reddit/reddit-upvotes-karma/)

---

## 3. Anomaly Detection Systems

### 3.1 Time Series Anomaly Detection

**What it solves**: Identifying unusual patterns in sequential data (e.g., sudden drops in heuristic success rate).

**State-of-the-art algorithms (2024)**:

#### Deep Learning Approaches
1. **LSTM-based methods**:
   - Learn temporal dependencies
   - Output anomaly score using One-Class SVM or SVDD
   - Good for long-term patterns

2. **Isolation Forest**:
   - Tree ensemble method
   - Anomalies are "easy to isolate" - few splits needed
   - Fast, scalable, no distance/density calculation
   - **Recommended for tabular data**

3. **Variational Autoencoders (VAE)**:
   - Encoder maps to latent space, decoder reconstructs
   - LSTM-VAE handles sequences
   - OmniAnomaly: First to model temporal dependencies between latent variables
   - High reconstruction error = anomaly

4. **Transformers**:
   - Self-attention mechanisms capture long-range dependencies
   - Promising results in multivariate time series

5. **Graph Neural Networks (GNNs)**:
   - Model relationships between time periods as graph
   - Capture interdependencies between variables

#### Ensemble Methods
- Combine multiple algorithms (bagging, boosting, stacking)
- Overcomes individual model limitations
- Higher accuracy and robustness

**Applicability to ELF**:
- ✅ **Isolation Forest**: Detect fraudulent heuristics (anomalous validation patterns)
- ✅ **LSTM + One-Class SVM**: Learn normal confidence trajectories, flag deviations
- ⚠️ Deep learning requires substantial training data
- 💡 **Start simple (Isolation Forest), add complexity as data accumulates**

**Sources**:
- [Deep Learning for Time Series Anomaly Detection Survey (2024)](https://dl.acm.org/doi/10.1145/3691338)
- [Anomaly Detection in Multivariate Time Series (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11156414/)
- [Machine Learning Approaches to Time Series Anomaly Detection](https://www.anomalo.com/blog/machine-learning-approaches-to-time-series-anomaly-detection/)

---

### 3.2 Fraud Detection in Financial Systems

**What it solves**: Real-time identification of fraudulent transactions in high-volume streams.

**Key techniques**:
1. **Behavioral analytics**: Model normal user behavior, flag deviations
2. **Graph analysis**: Detect money-laundering rings through transaction networks
3. **Ensemble classifiers**: Combine rule-based, statistical, and ML approaches
4. **Real-time scoring**: Sub-second fraud probability calculation
5. **Adaptive thresholds**: Adjust sensitivity based on risk tolerance and false positive rates

**Lessons for ELF**:
- ✅ **Multi-signal detection**: Don't rely on single metric
- ✅ **Graph analysis**: Model relationships between heuristics, detect circular validation
- ✅ **Adaptive thresholds**: Fraud sensitivity should tune based on observed patterns

**Sources**: Previous search results on eBay fraud detection and time-series anomaly detection papers.

---

## 4. Trust & Confidence Scoring

### 4.1 PageRank and Sybil Vulnerabilities

**What it solves**: Ranking web pages by authority based on link structure.

**How it works**:
- Random walk algorithm: probability of reaching page by following links
- Pages linked by authoritative pages gain authority
- Damping factor (0.85): probability of continuing vs. random jump

**Sybil attack vulnerability**:
- Attackers create dense Sybil regions (many interconnected fake nodes)
- Cycle attacks: Large weights among Sybil nodes inflate scores unboundedly
- **PageRank is NOT Sybil-tolerant**

**Why it fails**:
- No knowledge of node quality, only structure
- Cannot distinguish genuine popularity from manufactured links
- Attack edges not required - internal Sybil structure sufficient

**Applicability to ELF**:
- ❌ **Do NOT use pure PageRank-style propagation** for heuristic authority
- ⚠️ Graph-based trust can be gamed through circular validation

**Source**: [Manipulability of PageRank under Sybil Strategies](https://www.researchgate.net/publication/200110773_Manipulability_of_PageRank_under_Sybil_Strategies)

---

### 4.2 TrustRank for Spam Resistance

**What it solves**: Differentiate good and spam websites by seeding trust from expert-validated sources.

**How it works**:
1. Expert manually evaluates small seed set of trusted pages
2. Trust propagates through links, decaying with distance
3. Spam pages (far from trusted seeds) receive low trust
4. Inverse of spam rank also calculated (seed from known spam)

**Advantages over PageRank**:
- Explicitly incorporates quality judgments
- Spam sites cannot boost trust through internal links alone
- Requires connection to trusted seed set

**Applicability to ELF**:
- ✅ **Seed with golden rules**: Manually validated heuristics start with high trust
- ✅ **Trust decay**: Derived heuristics have lower initial trust
- ✅ **Dual scoring**: Both "trust" and "spam" scores
- ⚠️ Requires identifying trusted seed set

**Source**: [Combating Web Spam with TrustRank](https://www.vldb.org/conf/2004/RS15P3.PDF)

---

### 4.3 Personalized PageRank (PPR)

**What it solves**: Sybil-resistant ranking by biasing random walk toward trusted seed nodes.

**How it works**:
- Standard random walk, but with probability α, jump back to seed node
- Damping factor limits exposure to Sybil regions
- Honest nodes can whitelist trustworthy nodes efficiently

**Sybil resistance**:
- ✅ Resistant when no attack edges exist (Sybil region isolated)
- ❌ Vulnerable if Sybil nodes connect to honest network
- 🎯 **Effectiveness depends on limiting attack edges**

**Applicability to ELF**:
- ✅ **Personalized trust**: Each user's perspective on heuristic trust
- ✅ **Seed from their own validated heuristics**
- ⚠️ Attack edges = fraudulent cross-validation

**Source**: [SoK: The Evolution of Sybil Defense via Social Networks](https://www.cs.cornell.edu/lorenzo/papers/Alvisi13SoK.pdf)

---

### 4.4 Modern Blockchain Approaches (2024)

**What it solves**: Sybil resistance in decentralized networks without central authority.

**Key mechanisms**:
1. **Proof of Work (PoW)**: Computational cost makes identity creation expensive
2. **Proof of Stake (PoS)**: Must stake valuable assets, losing value if malicious
3. **Reputation-weighted ranking**: Payment transactions as endorsements
   - TraceRank: Seeds addresses with precomputed reputation
   - Propagates through transaction graph weighted by value and recency
   - **Spam services with many low-reputation payers rank below legitimate services with few high-reputation payers**

**Applicability to ELF**:
- ✅ **Stake-based validation**: Agents with high reputation lose more by fraudulent validation
- ✅ **Economic deterrence**: Cost of gaming > benefit
- ⚠️ Assumes rational actors, doesn't prevent all attacks

**Source**: [Blockchain's Biggest Threat: How New Defenses Are Crushing Sybil Attacks (2024)](https://mni.is/news_en/16220/blockchains-biggest-threat-how-new-defenses-are-crushing-sybil-attacks-in-2024/)

---

### 4.5 Academic Trust Metrics (2024 Research)

**Recent findings on confidence scoring**:

1. **Trust in AI models** (Nature 2024): AI familiarity is strongest predictor, followed by age and gender
   - Implication: Domain expertise affects how users trust heuristics

2. **Miscalibrated confidence** (arXiv 2024): Displaying AI confidence scores affects user trust
   - Over-confident AI reduces trust when errors occur
   - Under-confident AI reduces reliance even when correct
   - **Calibration matters more than raw accuracy**

3. **ML model trust assessment** (PMC 2024): Three perspectives
   - **Robustness**: Stability across perturbations
   - **Confidence intervals**: 95% CI of performance metric
   - **Interpretability**: Feature importance rankings

4. **ACM Survey on ML-based trust evaluation**:
   - Trust evaluation quantifies trust using attributes
   - ML overcomes data scarcity and automation needs
   - Challenge: Defining appropriate trust attributes

**Applicability to ELF**:
- ✅ **Confidence calibration**: Display realistic confidence, not inflated scores
- ✅ **Multi-faceted trust**: Robustness + confidence + interpretability
- ✅ **Domain-aware**: Expert users vs. novices may weight trust differently

**Sources**:
- [Modeling Public Trust in AI (Nature 2024)](https://www.nature.com/articles/s41598-025-23447-4)
- [Effects of Miscalibrated AI Confidence (arXiv 2024)](https://arxiv.org/html/2402.07632v4)
- [Machine Learning Models' Assessment: Trust and Performance (PMC 2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11485107/)
- [ACM Survey on Trust Evaluation Based on ML](https://dl.acm.org/doi/10.1145/3408292)

---

## 5. Knowledge Graph Systems

### 5.1 Wikidata Approach to Conflicting Facts

**What it solves**: Representing factual knowledge where authoritative sources disagree.

**How confidence works**:
- Wikidata is "a database of assertions, not absolute truth"
- **Provenance tracking**: Each fact includes source reference
- **Qualifiers**: Additional context (e.g., "population in 2020: X, according to source Y")
- **Multiple values allowed**: Conflicting information stored with sources

**Handling contradictions**:
- No automatic resolution - contradictions preserved
- Users see multiple claims with provenance
- Downstream systems choose which source to trust based on authority/recency
- **Disagreement is a feature, not a bug**

**Quality issues identified**:
- Wikipedia/Wikidata contain expired and conflicting information
- Different language editions may disagree
- Not reliable as "ground truth" without verification

**Conflict resolution in DBpedia (Sieve module)**:
- **Quality assessment metrics**: Recency, source reputation
- **Fusion step**: Apply policies based on quality scores
- Example: Prefer most recent value from highest-reputation source

**Applicability to ELF**:
- ✅ **Provenance tracking**: Who validated this heuristic?
- ✅ **Context-aware contradictions**: Heuristic A works in frontend, fails in backend
- ✅ **No forced resolution**: Multiple valid approaches can coexist
- ⚠️ Requires UI to present conflicting heuristics clearly

**Sources**:
- [Uncertainty Management in Knowledge Graph Construction (2024)](https://arxiv.org/html/2405.16929v2)
- [Wikidata Conflicting Attributes](https://blog.gdeltproject.org/knowledge-graphs-over-wikidata-wikipedia-conflicting-attributes/)
- [Agreeing and Disagreeing in Wikidata (2023)](https://arxiv.org/html/2306.11766)

---

### 5.2 Knowledge Graph Confidence Scoring

**How it works**:
- **Knowledge alignment**: Identify duplicates, specificity differences, contradictions
- **Knowledge fusion**: Resolve conflicts, assign confidence scores
- **Quality estimation**: Rate data sources and extracted facts

**Methods**:
1. **Facebook Knowledge Graph**:
   - Remove low-confidence information
   - Integrate conflicting info with provenance and confidence

2. **DBpedia Sieve**:
   - Compute recency and reputation metrics
   - Apply fusion policy (e.g., "newest from best source")

3. **UKGSE (Uncertain KG Subgraph Embedding)**:
   - Captures subgraph structural features
   - Predicts confidence scores for triplets
   - Uses neighborhood information, not just isolated facts

**LLM verification (2024)**:
- ChatWikiDP system: Identifies entities/claims in LLM outputs
- Verifies against Wikidata structured data
- Visual highlighting of valid vs. unverified claims

**Applicability to ELF**:
- ✅ **Subgraph features**: Heuristic confidence depends on neighboring heuristics
- ✅ **Source quality**: Weight validations by validator reputation
- ✅ **LLM integration**: Auto-extract heuristics from LLM conversations, verify against DB
- 💡 **Graph embedding approach could be powerful for complex heuristic relationships**

**Sources**:
- [Uncertainty Management in Knowledge Graph Construction Survey](https://drops.dagstuhl.de/storage/08tgdk/tgdk-vol003/tgdk-vol003-issue001/TGDK.3.1.3/TGDK.3.1.3.pdf)
- [Fact Checking Knowledge Graphs Survey (2024)](https://dl.acm.org/doi/10.1145/3749838)

---

## 6. Machine Learning Approaches

### 6.1 Online Learning and Concept Drift

**What it solves**: Adapting models when data distributions change over time (e.g., heuristic effectiveness shifts as codebase evolves).

**Concept drift types**:
1. **Abrupt drift**: Sudden change (e.g., framework migration)
2. **Gradual drift**: Slow transition (e.g., codebase growing)
3. **Incremental drift**: Step-wise changes
4. **Recurring drift**: Patterns repeat (e.g., seasonal development cycles)

**Key algorithms**:

#### ADWIN (Adaptive Windowing) - **RECOMMENDED**
- Maintains sliding window, splits into old/new subwindows
- Detects drift when mean difference exceeds threshold
- **Advantages**:
  - No parameters to tune
  - Handles both gradual and abrupt drift
  - Provable error bounds
  - Window grows during stability, shrinks during drift
- **Disadvantages**:
  - Higher memory usage than fixed windows

#### DDM (Drift Detection Method)
- Monitors error rate and standard deviation
- Assumes binomial distribution of errors
- **Advantages**: Simple, well-understood
- **Disadvantages**: Ineffective for gradual drift, requires minimum errors to initialize

#### EDDM (Early Drift Detection Method)
- Monitors distance between errors, not error rate
- Better for gradual drift than DDM
- **Disadvantages**: Sensitive to noise, longest detection delays in benchmarks

**Comparative performance (2023 benchmark)**:
- ADWIN: Best overall, handles all drift types
- EDDM: Longest delays, highest false negatives
- DDM: Good for abrupt drift, misses gradual drift

**Applicability to ELF**:
- ✅ **ADWIN for confidence score drift detection**
- ✅ **Monitor heuristic success rate changes**
- ✅ **Auto-adjust confidence when context changes**
- 💡 **Implement drift detection per heuristic-domain pair**

**Sources**:
- [Concept Drift Detection Methods](https://www.aporia.com/learn/data-drift/concept-drift-detection-methods/)
- [Benchmarking Change Detector Algorithms (2023)](https://www.mdpi.com/1999-5903/15/5/169)
- [Concept Drift Detection Guide](https://indialindsay1.medium.com/concept-drift-detection-2667a3360091)

---

### 6.2 Multi-Armed Bandits for Exploration/Exploitation

**What it solves**: Balancing trying new heuristics (exploration) vs. using known-good ones (exploitation).

**Classic algorithms**:
1. **ε-greedy**: Exploit best arm with probability 1-ε, explore randomly with probability ε
2. **UCB (Upper Confidence Bound)**: Choose arm maximizing `mean + sqrt(2*log(t)/n)`
3. **Thompson Sampling**: Bayesian approach, sample from posterior distributions

**Non-stationary bandits** (for concept drift):
1. **Discounted UCB**: Weight recent rewards more heavily
2. **Sliding-Window UCB**: Only consider recent N observations
3. **f-dsw Thompson Sampling**: Discount factor + sliding window

**2024 research - OMS-MAB**:
- **Application**: Concept drift adaptation in streaming data
- **Approach**: Ensemble of drift-resistant learners, each represented as bandit arm
- **ε-exploration factor**: Tune trade-off between performance and computational cost
- **Result**: Efficient model selection under drift

**Applicability to ELF**:
- ✅ **Heuristic selection as multi-armed bandit**: Each heuristic is an arm
- ✅ **Reward = success rate** in recent validations
- ✅ **Sliding-window approach** handles context drift
- ✅ **ε-greedy parameter**: Tune exploration based on risk tolerance
- 💡 **Contextual bandits**: Features = task type, domain, user expertise

**Sources**:
- [Multi-Armed Bandit for Concept Drift Adaptation (2024)](https://www.researchgate.net/publication/380597154_Multi-armed_bandit_based_online_model_selection_for_concept-drift_adaptation)
- [Non-Stationary Multi-Armed Bandit with Concept Drift (2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8004723/)
- [Multi-Armed Bandits in ML Deployment (2025 preprint)](https://arxiv.org/html/2503.22595)

---

### 6.3 Reinforcement Learning for Heuristic Discovery

**What it solves**: Automatically discovering and optimizing heuristics through trial and error.

**Hyper-heuristics**:
- **Meta-level**: RL agent selects which low-level heuristic to apply
- **Learning component**: Agent adjusts strategy based on effectiveness
- **Global search + learning**: Combines HH exploration with RL adaptation

**2024 research highlights**:

1. **Nature: Discovering RL Algorithms Autonomously**:
   - Meta-learning discovers RL rules from population experiences
   - State-of-the-art on challenging benchmarks
   - Learned rules generalize across environments

2. **Q-Learning Meta-Heuristics (QLMA)**:
   - Applied to genetic algorithms, PSO, ant colony
   - Leading solution in energy, power systems, engineering
   - Q-learning guides which mutation/crossover operators to use

3. **Learning Heuristic Functions**:
   - Deep Q-networks learn domain-specific heuristics
   - Guide A* search in planning problems
   - "Domain-independent" learning of domain-specific functions

4. **RL-based Acceptance Criteria**:
   - Q-learning decides whether to accept/reject solution in metaheuristics
   - Applied to simulated annealing and artificial bee colony
   - Online and offline variants

**Applicability to ELF**:
- ✅ **Meta-heuristics**: RL selects which heuristic to suggest
- ✅ **Policy learning**: Discover patterns in when heuristics work
- ⚠️ Requires substantial trial data
- 💡 **Long-term goal**: ELF learns to generate new heuristics, not just score existing ones

**Sources**:
- [Discovering State-of-the-Art RL Algorithms (Nature 2025)](https://www.nature.com/articles/s41586-025-09761-x)
- [RL-Based Hyper-Heuristics Review (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11232579/)
- [Q-Learning Meta-Heuristic Algorithms (2024)](https://wires.onlinelibrary.wiley.com/doi/full/10.1002/widm.1548)
- [Machine Learning-Based Hyper-Heuristics (2024)](https://dl.acm.org/doi/10.1145/3708778.3708783)

---

## 7. Algorithm Recommendations

### 7.1 Fraud Detection: What Works in Practice

**Recommended approach: Multi-layered defense**

#### Layer 1: Statistical Anomaly Detection
- **Algorithm**: Isolation Forest
- **Why**: Fast, scalable, no training required, handles multivariate data
- **Apply to**: Validation patterns (time between validations, validation sources, confidence trajectories)
- **Threshold**: Flag top 1-5% anomalous patterns for review

#### Layer 2: Graph Analysis
- **Algorithm**: Community detection (Louvain algorithm)
- **Why**: Identifies circular validation rings
- **Apply to**: Validator-heuristic bipartite graph
- **Threshold**: Flag communities with >80% internal validation rate

#### Layer 3: Rate-Based Detection
- **Algorithm**: ADWIN on validation rate
- **Why**: Detects sudden spikes in validations (botting)
- **Apply to**: Per-user validation rate
- **Threshold**: Alert on drift detection

#### Layer 4: Behavioral Heuristics
- **Simple rules** (inspired by eBay/Stack Overflow):
  - New user with >10 validations in first hour: Flag
  - User validates only one other user's heuristics: Flag
  - Validation timestamps exactly regular (bot-like): Flag
  - User validates before heuristic has validations from others: Weight lower

**Implementation priority**: Layer 4 → Layer 1 → Layer 3 → Layer 2

---

### 7.2 Smoothing: Best Approaches from Literature

**Recommended: Exponentially Weighted Moving Average (EWMA)**

**Why EWMA**:
1. **Recursive computation**: `EWMA_t = α * value_t + (1-α) * EWMA_{t-1}`
   - No need to store all history
   - Constant memory and computation

2. **Recent bias**: Exponentially decays old values
   - More responsive than simple moving average
   - Smooths noise while tracking trends

3. **Single parameter α** (smoothing factor):
   - α = 0.1: Very smooth, slow to respond (stable environments)
   - α = 0.3: Balanced (recommended starting point)
   - α = 0.5: Responsive, less smoothing (volatile environments)
   - **Can tune per heuristic based on validation frequency**

4. **Well-studied**: Standard in finance, time-series forecasting, control systems

**Alternatives for specific needs**:
- **Holt-Winters**: If seasonal patterns emerge (e.g., weekday vs. weekend development)
- **Kalman filter**: If you model confidence as hidden state with noise
- **Median filter**: If you need robustness to outliers (malicious validations)

**Implementation**:
```python
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
# Or use pandas: df['confidence'].ewm(alpha=0.3).mean()
```

**Source**: [Exponential Smoothing for Time Series Forecasting](https://www.geeksforgeeks.org/artificial-intelligence/exponential-smoothing-for-time-series-forecasting/)

---

### 7.3 Trend Detection: Standard Algorithms

**Recommended: ADWIN + Mann-Kendall Test**

#### ADWIN (Adaptive Windowing)
- **Purpose**: Detect when confidence distribution changes
- **Output**: Binary signal (drift detected / no drift)
- **Use case**: "This heuristic's effectiveness has changed"

#### Mann-Kendall Trend Test
- **Purpose**: Detect monotonic trends (increasing/decreasing)
- **Output**: Trend direction + statistical significance
- **Use case**: "This heuristic is gaining/losing effectiveness over time"

**Combined approach**:
1. Run ADWIN continuously for drift detection
2. When ADWIN signals drift, run Mann-Kendall on recent window
3. Classify: Abrupt change vs. gradual trend
4. Update heuristic metadata with trend direction

**Implementation**:
```python
from river.drift import ADWIN
from scipy.stats import kendalltau  # Or use pymannkendall library
```

**Source**: [scikit-multiflow ADWIN documentation](https://scikit-multiflow.readthedocs.io/en/stable/api/generated/skmultiflow.drift_detection.ADWIN.html)

---

### 7.4 Domain Management: How Others Handle Limits

**Approaches from literature**:

1. **Hard limits (Stack Overflow badges)**:
   - Fixed criteria: "100 upvotes on tag X"
   - Simple, transparent, but rigid

2. **Soft boundaries (Wikidata)**:
   - No enforcement of domain limits
   - Users manually tag domains, conflicts preserved
   - Flexible but messy

3. **Learned boundaries (Bayesian Networks)**:
   - Model domain as latent variable
   - Learn conditional probabilities: P(success | heuristic, domain)
   - Data-driven, but requires training data

4. **Hierarchical domains (Reddit subreddits)**:
   - Tree structure: programming > python > django
   - Heuristic can apply at multiple levels
   - Allows generalization and specialization

**Recommended for ELF: Hierarchical + learned boundaries**
- Start with user-specified hierarchy (manual tagging)
- Learn domain applicability from validation data
- Use Dempster-Shafer to represent belief: "This heuristic applies to {frontend, testing}" with confidence scores
- Allow contradictions: Can work in A, fail in B, unknown for C

---

## 8. Patterns to Adopt

### Pattern 1: Dempster-Shafer Confidence Modeling
**Source**: Expert systems literature (MYCIN, Dempster-Shafer theory)

**What**: Represent confidence as belief masses over sets of possibilities, not point probabilities.

**Why**:
- Distinguishes "no evidence" from "50% confident"
- Handles domain applicability naturally ("works for {frontend, backend}")
- Conflict coefficient K detects contradictory evidence (fraud indicator)

**How**:
```python
class HeuristicBelief:
    def __init__(self):
        self.mass = {}  # Set -> probability mass

    def add_evidence(self, applicable_domains: set, confidence: float):
        # Dempster's combination rule
        pass

    def conflict(self) -> float:
        # Return K (conflict coefficient)
        # High K = contradictory evidence
        pass
```

**Citation**: [The Dempster-Shafer Theory of Evidence](https://www.researchgate.net/publication/242392452_The_Dempster-Shafer_theory_of_evidence)

---

### Pattern 2: EWMA Smoothing with Adaptive Alpha
**Source**: Time series forecasting, control systems

**What**: Smooth confidence scores using exponentially weighted moving average, tune α based on validation frequency.

**Why**:
- Recursive (constant memory/computation)
- Recent bias (new evidence matters more)
- Self-tuning: High validation frequency → lower α (more smoothing)

**How**:
```python
def update_confidence(current_ewma, new_validation, validations_per_week):
    # More validations → more smoothing (lower alpha)
    alpha = 0.5 if validations_per_week < 1 else 0.3 if validations_per_week < 10 else 0.1
    return alpha * new_validation + (1 - alpha) * current_ewma
```

**Citation**: [Exponential Smoothing for Time Series Forecasting](https://www.geeksforgeeks.org/artificial-intelligence/exponential-smoothing-for-time-series-forecasting/)

---

### Pattern 3: TrustRank Seeding from Golden Rules
**Source**: Web spam detection (TrustRank algorithm)

**What**: Seed trust propagation from manually validated golden rules.

**Why**:
- Prevents bootstrap problem (new heuristics need initial trust)
- Limits Sybil attack impact (must connect to trusted seed)
- Aligns with ELF philosophy (golden rules are foundational)

**How**:
```python
def initialize_trust():
    trust_scores = {}
    for rule in golden_rules:
        trust_scores[rule.id] = 1.0  # Maximum trust

    for heuristic in all_heuristics:
        if heuristic.derived_from:
            # Trust decays with derivation distance
            trust_scores[heuristic.id] = trust_scores[heuristic.derived_from] * 0.8
        else:
            trust_scores[heuristic.id] = 0.5  # Neutral starting trust
```

**Citation**: [Combating Web Spam with TrustRank](https://www.vldb.org/conf/2004/RS15P3.PDF)

---

### Pattern 4: Diminishing Returns on Validations
**Source**: Reddit karma system

**What**: Each additional validation contributes less to confidence score.

**Why**:
- Prevents single coordinated event from dominating
- Encourages diverse validation sources
- Natural ceiling on confidence

**How**:
```python
def marginal_confidence_boost(num_existing_validations):
    # First validation: +0.3, tenth validation: +0.03
    return 0.3 / (1 + num_existing_validations * 0.1)
```

**Citation**: [Reddit Karma Explained](https://karmatic.ai/how-does-reddit-karma-work-a-complete-guide-for-new-and-experienced-redditors/)

---

### Pattern 5: Isolation Forest for Fraud Detection
**Source**: Anomaly detection literature (2024 surveys)

**What**: Detect fraudulent heuristics by identifying anomalous validation patterns.

**Why**:
- No training required (unsupervised)
- Fast and scalable
- Naturally handles multivariate patterns (validation rate, source diversity, timing)

**How**:
```python
from sklearn.ensemble import IsolationForest

def detect_fraud(heuristics):
    features = np.array([
        [h.validations_per_day, h.unique_validators, h.avg_time_between_validations]
        for h in heuristics
    ])

    clf = IsolationForest(contamination=0.05)  # Expect 5% fraud
    predictions = clf.fit_predict(features)

    return [h for h, pred in zip(heuristics, predictions) if pred == -1]
```

**Citation**: [Machine Learning Approaches to Time Series Anomaly Detection](https://www.anomalo.com/blog/machine-learning-approaches-to-time-series-anomaly-detection/)

---

### Pattern 6: ADWIN Drift Detection per Heuristic
**Source**: Concept drift detection (scikit-multiflow)

**What**: Monitor each heuristic's success rate for distribution changes.

**Why**:
- No parameters to tune
- Handles gradual and abrupt drift
- Signals when context has changed (heuristic outdated or misclassified domain)

**How**:
```python
from river.drift import ADWIN

heuristic_monitors = {h.id: ADWIN() for h in heuristics}

def record_validation(heuristic_id, success: bool):
    adwin = heuristic_monitors[heuristic_id]
    adwin.update(1 if success else 0)

    if adwin.drift_detected:
        # Context change detected
        mark_heuristic_for_review(heuristic_id)
        adwin.reset()
```

**Citation**: [Concept Drift Detection Methods](https://www.aporia.com/learn/data-drift/concept-drift-detection-methods/)

---

### Pattern 7: Multi-Armed Bandit for Heuristic Selection
**Source**: RL for concept drift adaptation (2024 research)

**What**: Treat heuristic selection as bandit problem - balance exploiting known-good heuristics with exploring new ones.

**Why**:
- Naturally handles exploration/exploitation trade-off
- Adapts to changing effectiveness (non-stationary bandits)
- Provable regret bounds

**How**:
```python
from river.bandit import UCB

def select_heuristic_for_task(task_context, available_heuristics):
    bandit = contextual_bandits[task_context]

    # Select heuristic using Upper Confidence Bound
    selected = bandit.pull()

    # After task, update with reward
    success = apply_heuristic(selected, task_context)
    bandit.update(selected, reward=1 if success else 0)

    return selected
```

**Citation**: [Multi-Armed Bandit for Concept Drift Adaptation](https://www.researchgate.net/publication/380597154_Multi-armed_bandit_based_online_model_selection_for_concept-drift_adaptation)

---

### Pattern 8: Provenance Tracking (Wikidata-style)
**Source**: Knowledge graphs (Wikidata, DBpedia)

**What**: Store source of every validation, allow contradictory evidence.

**Why**:
- Enables source quality weighting
- Supports forensic analysis of fraud
- Allows contradictions to coexist with context

**How**:
```sql
CREATE TABLE validations (
    id INTEGER PRIMARY KEY,
    heuristic_id INTEGER,
    validator_id INTEGER,
    outcome BOOLEAN,
    context TEXT,  -- JSON: {domain, task_type, etc.}
    timestamp DATETIME,
    provenance TEXT  -- "Applied to project X, task Y"
);
```

**Citation**: [Uncertainty Management in Knowledge Graph Construction](https://arxiv.org/html/2405.16929v2)

---

### Pattern 9: Vote Fuzzing for Display
**Source**: Reddit vote system

**What**: Add random noise to displayed confidence scores (not underlying data).

**Why**:
- Deters manipulation (can't verify impact)
- Minimal implementation cost
- Preserves true data for analysis

**How**:
```python
def display_confidence(true_confidence: float, num_validations: int) -> float:
    if num_validations < 5:
        return true_confidence  # No fuzzing for new heuristics

    noise_scale = min(0.1, num_validations * 0.002)  # Up to ±10%
    noise = random.gauss(0, noise_scale)

    return max(0.0, min(1.0, true_confidence + noise))
```

**Citation**: [What is Reddit's Voting System?](https://dicloak.com/blog-detail/what-is-reddits-voting-system-heres-how-it-works)

---

### Pattern 10: Confidence Calibration Metrics
**Source**: AI trust research (2024 academic surveys)

**What**: Measure and display calibration (alignment between confidence and actual success rate).

**Why**:
- Over-confident heuristics reduce trust when they fail
- Under-confident heuristics are underutilized
- Calibration matters more than raw accuracy for user trust

**How**:
```python
def calibration_error(heuristic):
    bins = [(0.0, 0.2), (0.2, 0.4), ..., (0.8, 1.0)]

    for low, high in bins:
        predictions = [v for v in validations if low <= v.confidence < high]
        avg_confidence = np.mean([v.confidence for v in predictions])
        actual_success = np.mean([v.outcome for v in predictions])

        error += abs(avg_confidence - actual_success)

    return error / len(bins)
```

**Citation**: [Effects of Miscalibrated AI Confidence](https://arxiv.org/html/2402.07632v4)

---

## 9. Anti-Patterns to Avoid

### Anti-Pattern 1: Pure PageRank-Style Propagation
**Why it fails**: Vulnerable to Sybil attacks via cycle attacks and dense Sybil regions.

**Evidence**: Research shows PageRank can be manipulated unboundedly without attack edges to honest network.

**What to do instead**: Use TrustRank (seed-based) or Personalized PageRank (biased random walk).

**Source**: [Manipulability of PageRank under Sybil Strategies](https://www.researchgate.net/publication/200110773_Manipulability_of_PageRank_under_Sybil_Strategies)

---

### Anti-Pattern 2: Ignoring Temporal Dynamics
**Why it fails**: Static confidence scores don't adapt to changing contexts.

**Evidence**: eBay found that recent feedback matters more; Reddit archives old posts; Stack Overflow research shows reputation decay needed.

**What to do instead**: Implement time decay (EWMA, sliding windows) and drift detection (ADWIN).

**Source**: Multiple sources on reputation systems and concept drift.

---

### Anti-Pattern 3: Binary Success/Failure
**Why it fails**: Loses nuance; doesn't capture partial applicability or conditional success.

**Evidence**: eBay's binary positive/negative lost nuance; evolved to multi-dimensional seller ratings.

**What to do instead**: Multi-faceted success metrics (speed, reliability, applicability) or context-conditional outcomes.

**Source**: [eBay Reputation System Research](https://cs.stanford.edu/people/eroberts/courses/cs181/projects/2010-11/PsychologyOfTrust/rep2.html)

---

### Anti-Pattern 4: No Cost for Negative Feedback
**Why it fails**: Encourages frivolous challenges and downvoting attacks.

**Evidence**: Stack Overflow charges -1 reputation for downvoting to prevent casual negativity.

**What to do instead**: Small cost for challenging heuristic (reputation stake, time investment).

**Source**: [Stack Overflow Reputation Gaming Research](https://dl.acm.org/doi/10.1145/3691627)

---

### Anti-Pattern 5: Single Anomaly Detection Method
**Why it fails**: Each method has blind spots; sophisticated fraud exploits weaknesses.

**Evidence**: eBay, financial systems, and research consensus: multi-layered defense is essential.

**What to do instead**: Layer statistical (Isolation Forest) + graph (community detection) + rate-based (ADWIN) + behavioral heuristics.

**Source**: [Inside eBay's Real-Time Auction System](https://www.frugaltesting.com/blog/inside-ebays-real-time-auction-system-bidding-logic-algorithms-fraud-prevention-techniques)

---

### Anti-Pattern 6: Forced Conflict Resolution
**Why it fails**: Multiple valid approaches can coexist in different contexts; forcing single "truth" loses information.

**Evidence**: Wikidata intentionally preserves conflicting facts with provenance; DBpedia Sieve only resolves when necessary.

**What to do instead**: Store contradictions with context; let users choose or apply context-based resolution.

**Source**: [Wikidata Conflicting Attributes](https://blog.gdeltproject.org/knowledge-graphs-over-wikidata-wikipedia-conflicting-attributes/)

---

### Anti-Pattern 7: Uniform Confidence Increments
**Why it fails**: Allows gaming through volume; doesn't account for validation source quality or diversity.

**Evidence**: Reddit implements diminishing returns; Stack Overflow weights by user reputation.

**What to do instead**: Implement diminishing returns + source quality weighting.

**Source**: [Reddit Karma System](https://karmatic.ai/how-does-reddit-karma-work-a-complete-guide-for-new-and-experienced-redditors/)

---

### Anti-Pattern 8: Transparent Scoring Algorithm
**Why it fails**: Enables reverse-engineering optimal gaming strategies.

**Evidence**: Reddit keeps vote-to-karma conversion proprietary; eBay doesn't publish fraud detection criteria.

**What to do instead**: Publish principles (fairness, recency-weighting) but obscure exact formulas. Use vote fuzzing.

**Source**: [What is Reddit's Voting System?](https://dicloak.com/blog-detail/what-is-reddits-voting-system-heres-how-it-works)

---

### Anti-Pattern 9: No Bootstrap Mechanism
**Why it fails**: New heuristics can't gain traction without initial validation; new users can't validate without reputation.

**Evidence**: Stack Overflow newcomers struggle to earn first reputation points; reputation thresholds create barriers.

**What to do instead**: Seed from golden rules (TrustRank), give new heuristics "probationary" status, allow initial validations from any user.

**Source**: [Stack Overflow Research Roadmap](https://stackoverflow.blog/2024/11/04/research-roadmap-update-november-2024/)

---

### Anti-Pattern 10: Ignoring Calibration
**Why it fails**: Users lose trust in over-confident predictions; under-confident predictions underutilized.

**Evidence**: 2024 research shows miscalibrated AI confidence harms trust more than low accuracy.

**What to do instead**: Measure and display calibration error; tune confidence scores to match actual success rates.

**Source**: [Effects of Miscalibrated AI Confidence](https://arxiv.org/html/2402.07632v4)

---

## 10. Open Source Libraries

### 10.1 Anomaly Detection

#### PyOD (Python Outlier Detection) - **HIGHLY RECOMMENDED**
- **Version**: 2.0.6 (December 2024 update)
- **Features**: 45+ algorithms (LOF, Isolation Forest, One-Class SVM, Autoencoders)
- **Installation**: `pip install pyod`
- **Why use it**:
  - Unified scikit-learn-style API
  - LLM-powered model selection in v2
  - 26 million downloads, battle-tested
  - Includes deep learning models (PyTorch-based)

**Example**:
```python
from pyod.models.iforest import IForest
clf = IForest(contamination=0.05)
clf.fit(X_train)
anomaly_scores = clf.decision_function(X_test)
```

**Citation**: [PyOD 2: A Python Library for Outlier Detection with LLM-powered Model Selection](https://arxiv.org/abs/2412.12154)

**GitHub**: https://github.com/yzhao062/pyod

---

#### scikit-learn
- **Algorithms**: Isolation Forest, One-Class SVM, Local Outlier Factor
- **Installation**: `pip install scikit-learn`
- **Why use it**: Standard ML library, minimal dependencies

**Example**:
```python
from sklearn.ensemble import IsolationForest
clf = IsolationForest(random_state=42)
clf.fit(X)
predictions = clf.predict(X)  # -1 for outliers
```

---

### 10.2 Concept Drift Detection

#### River (Merger of scikit-multiflow and Creme) - **RECOMMENDED**
- **Focus**: Online machine learning and streaming data
- **Installation**: `pip install river`
- **Drift detectors**: ADWIN, DDM, EDDM, HDDM, Page-Hinkley
- **Why use it**:
  - Modern, actively maintained
  - Clean API
  - Integrated with online learning algorithms

**Example**:
```python
from river import drift

adwin = drift.ADWIN()

for x in data_stream:
    adwin.update(x)
    if adwin.drift_detected:
        print("Drift detected!")
```

**GitHub**: https://github.com/online-ml/river

---

#### scikit-multiflow (Legacy, use River instead)
- **Status**: Development moved to River
- **Still available**: Code remains on GitHub/PyPI
- **Use if**: Need exact replication of old experiments

---

### 10.3 Time Series Smoothing

#### statsmodels - **RECOMMENDED**
- **Installation**: `pip install statsmodels`
- **Features**: Simple, Double, Triple Exponential Smoothing (Holt-Winters)
- **Why use it**: Industry standard, comprehensive statistical models

**Example**:
```python
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

model = SimpleExpSmoothing(data)
fit = model.fit(smoothing_level=0.3, optimized=False)
forecast = fit.forecast(steps=10)
```

---

#### Pandas (built-in EWMA)
- **Installation**: `pip install pandas` (usually already installed)
- **Why use it**: No extra dependencies, simple API

**Example**:
```python
import pandas as pd

smoothed = df['confidence'].ewm(alpha=0.3).mean()
```

---

### 10.4 Multi-Armed Bandits

#### River (yes, again)
- **Bandits**: UCB, Thompson Sampling, EXP3, ε-greedy
- **Contextual bandits**: Available

**Example**:
```python
from river import bandit

ucb = bandit.UCB(delta=1.0)

for t in range(1000):
    arm = ucb.pull()
    reward = get_reward(arm)
    ucb.update(arm, reward)
```

---

### 10.5 Graph Analysis

#### NetworkX
- **Installation**: `pip install networkx`
- **Features**: Graph construction, community detection (Louvain), centrality measures
- **Why use it**: Python standard for graph analysis

**Example**:
```python
import networkx as nx
from networkx.algorithms import community

G = nx.Graph()
# Add edges...

communities = community.louvain_communities(G)
```

---

### 10.6 Directly Usable Code

**PyOD Isolation Forest for Fraud Detection**:
```python
from pyod.models.iforest import IForest
import numpy as np

# Extract features: validations_per_day, unique_validators, avg_time_between
features = np.array([[h.val_rate, h.n_validators, h.avg_time] for h in heuristics])

clf = IForest(contamination=0.05, random_state=42)
clf.fit(features)

outlier_scores = clf.decision_function(features)
is_fraud = clf.predict(features)  # -1 = outlier (fraud)

fraud_heuristics = [h for h, pred in zip(heuristics, is_fraud) if pred == -1]
```

**River ADWIN for Drift Detection**:
```python
from river.drift import ADWIN

# One ADWIN per heuristic
monitors = {h.id: ADWIN() for h in heuristics}

def on_validation(heuristic_id, success):
    adwin = monitors[heuristic_id]
    adwin.update(1.0 if success else 0.0)

    if adwin.drift_detected:
        logger.warning(f"Drift detected in heuristic {heuristic_id}")
        # Mark for re-evaluation, adjust confidence, etc.
```

**Pandas EWMA for Smoothing**:
```python
import pandas as pd

# Assuming you have a DataFrame with columns: timestamp, heuristic_id, confidence
df = pd.DataFrame(validation_history)

# Group by heuristic, compute EWMA
smoothed = df.groupby('heuristic_id')['confidence'].ewm(alpha=0.3).mean()

# Update database with smoothed values
```

---

## 11. Academic Papers

### Foundational Papers

1. **Shafer, G. (1976). "A Mathematical Theory of Evidence."**
   - Foundational work on Dempster-Shafer theory
   - Introduces belief functions and combination rules
   - **Key insight**: Explicit modeling of ignorance

2. **Pearl, J. (1988). "Probabilistic Reasoning in Intelligent Systems."**
   - Bayesian networks for expert systems
   - Message-passing algorithms
   - **Key insight**: Efficient inference in probabilistic graphical models

3. **Shortliffe, E. H. & Buchanan, B. G. (1975). "A Model of Inexact Reasoning in Medicine."**
   - MYCIN expert system
   - Certainty factors for medical diagnosis
   - **Key insight**: Domain experts reason with uncertainty, not precise probabilities

---

### Recent Surveys (2024-2025)

4. **"Deep Learning for Time Series Anomaly Detection: A Survey" (ACM Computing Surveys, 2024)**
   - DOI: 10.1145/3691338
   - Comprehensive review of LSTM, VAE, Transformer approaches
   - **Key insight**: Ensemble methods outperform single models

5. **"Uncertainty Management in the Construction of Knowledge Graphs: A Survey" (TGDK, 2024)**
   - URL: https://arxiv.org/html/2405.16929v2
   - Knowledge alignment, fusion, confidence estimation
   - **Key insight**: Provenance tracking essential for conflict resolution

6. **"A Review of Reinforcement Learning Based Hyper-Heuristics" (PeerJ Computer Science, 2024)**
   - PMC: PMC11232579
   - RL for meta-heuristic selection
   - **Key insight**: Online learning adapts to changing problem characteristics

7. **"Fact Checking Knowledge Graphs - A Survey" (ACM Computing Surveys, 2024)**
   - DOI: 10.1145/3749838
   - Verification methods, confidence scoring
   - **Key insight**: LLMs + structured KGs enable automated fact-checking

8. **"A Survey on Trust Evaluation Based on Machine Learning" (ACM Computing Surveys)**
   - DOI: 10.1145/3408292
   - ML approaches to quantifying trust
   - **Key insight**: Multi-faceted trust (robustness + confidence + interpretability)

---

### Specific Algorithms & Techniques

9. **Gama, J., et al. (2014). "A Survey on Concept Drift Adaptation" (ACM Computing Surveys)**
   - Foundational survey on drift detection
   - Compares DDM, EDDM, ADWIN
   - **Key insight**: No single algorithm works for all drift types

10. **Bifet, A. & Gavalda, R. (2007). "Learning from Time-Changing Data with Adaptive Windowing"**
    - ADWIN algorithm
    - Provable error bounds
    - **Key insight**: Adaptive windows balance memory and responsiveness

11. **Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). "Isolation Forest" (ICDM)**
    - Isolation-based anomaly detection
    - **Key insight**: Anomalies are "few and different" - easy to isolate

12. **Gyöngyi, Z. & Garcia-Molina, H. (2004). "Combating Web Spam with TrustRank" (VLDB)**
    - URL: https://www.vldb.org/conf/2004/RS15P3.PDF
    - Seed-based trust propagation
    - **Key insight**: Spam cannot boost trust through internal links alone

---

### Applied Research (2024)

13. **"Reputation Gaming in Crowd Technical Knowledge Sharing" (ACM TOSEM, 2024)**
    - DOI: 10.1145/3691627
    - Stack Overflow gaming scenarios and detection algorithms
    - **Key insight**: Community detection identifies voting rings

14. **"Multi-armed Bandit Based Online Model Selection for Concept-drift Adaptation" (2024)**
    - OMS-MAB algorithm
    - **Key insight**: MAB provides efficient exploration/exploitation under drift

15. **"Discovering State-of-the-Art Reinforcement Learning Algorithms" (Nature, 2025)**
    - DOI: 10.1038/s41586-025-09761-x
    - Meta-learning discovers RL rules autonomously
    - **Key insight**: Learned algorithms generalize across environments

16. **"Understanding the Effects of Miscalibrated AI Confidence on User Trust" (arXiv 2024)**
    - URL: https://arxiv.org/html/2402.07632v4
    - Calibration impact on trust
    - **Key insight**: Calibration matters more than raw accuracy for trust

17. **"PyOD 2: A Python Library for Outlier Detection with LLM-powered Model Selection" (arXiv 2024)**
    - URL: https://arxiv.org/abs/2412.12154
    - LLM-guided algorithm selection
    - **Key insight**: Automated model selection reduces expertise barrier

---

## 12. FINDINGS

### Facts

[fact] **Dempster-Shafer theory explicitly models ignorance**: Unlike Bayesian probabilities, DS assigns belief mass to sets of hypotheses. Mass on the universal set = "no evidence" (distinct from 50% probability). Critical for heuristics with unknown domain applicability.

[fact] **ADWIN outperforms DDM/EDDM for drift detection**: 2023 benchmark showed ADWIN handles both gradual and abrupt drift with no parameter tuning. EDDM has longest delays and highest false negatives.

[fact] **Isolation Forest requires no training data**: Unsupervised algorithm detects anomalies by measuring average path length in random trees. Anomalies are "easy to isolate" with few splits. Ideal for fraud detection when labeled fraud examples are scarce.

[fact] **Reddit uses vote fuzzing to deter manipulation**: Displayed vote counts include random noise (±500 on popular posts). Prevents gaming verification by obscuring manipulation impact. Fuzzing intensity scales with popularity.

[fact] **Exponentially Weighted Moving Average (EWMA) is recursively computable**: Formula `EWMA_t = α * value_t + (1-α) * EWMA_{t-1}` requires only current value and previous EWMA. Constant memory and computation regardless of history length.

[fact] **PageRank is vulnerable to Sybil attacks**: Attackers create dense Sybil regions with high-weight cycles, unboundedly inflating reputation scores. Attack requires no connections to honest network. Pure link-based authority propagation is insufficient for fraud resistance.

[fact] **Stack Overflow detects voting rings via community detection algorithms**: Louvain algorithm identifies isolated/semi-isolated communities with circular voting patterns. Automatic flagging for moderator review.

[fact] **Wikidata preserves conflicting facts with provenance**: Designed as "database of assertions, not absolute truth." Multiple contradictory values stored with source references. No forced resolution when authoritative sources disagree.

[fact] **Miscalibrated AI confidence reduces user trust**: 2024 research shows over-confident AI loses trust when errors occur; under-confident AI reduces reliance even when correct. Calibration (alignment between confidence and actual success) matters more than raw accuracy.

[fact] **Multi-armed bandits provide provable exploration/exploitation trade-offs**: UCB, Thompson Sampling, and Exp3 algorithms have theoretical regret bounds. Non-stationary variants (discounted UCB, sliding-window TS) handle concept drift.

---

### Hypotheses

[hypothesis] **Combining Dempster-Shafer confidence with ADWIN drift detection creates self-correcting system**: DS conflict coefficient K spikes when evidence contradicts (fraud or context shift). ADWIN detects distribution changes. Together: K spike + ADWIN alert → automatic domain reclassification or fraud flag.

[hypothesis] **TrustRank seeding from golden rules prevents Sybil bootstrap attacks**: New fraudulent heuristics cannot gain trust without connections to golden-rule-derived lineage. Limits attack surface to compromising validators of existing trusted heuristics.

[hypothesis] **Diminishing returns + EWMA smoothing creates natural confidence ceiling**: Each validation contributes less; EWMA converges to weighted average of recent validations. Combined effect: confidence plateaus around true success rate, resistant to temporary manipulation spikes.

[hypothesis] **Contextual multi-armed bandits outperform static heuristic ranking**: Different heuristics work in different contexts (domain, task type, user expertise). Bandit learns context → heuristic mapping through exploration, adapts to drift via sliding windows. Testable via A/B test against static recommendation.

[hypothesis] **Graph embedding of heuristic relationships enables semantic fraud detection**: Fraudulent heuristics have anomalous graph neighborhood (disconnected from golden rule lineage, only validated by other suspicious heuristics). GNN-based embeddings may outperform feature-based Isolation Forest.

[hypothesis] **Layered fraud detection reduces false positive rate vs. single method**: Statistical (Isolation Forest) + graph (community detection) + rate (ADWIN) + behavioral heuristics. Each layer catches different attack types; consensus voting reduces false positives. Requires empirical validation.

---

### Blockers

[blocker] **No consensus on optimal smoothing parameter α for EWMA**: Literature recommends 0.1-0.5 depending on application. ELF needs domain-specific tuning. Proposal: Start with α=0.3, run A/B test with α=0.1 and α=0.5, measure calibration error. Blocked pending real validation data.

[blocker] **Dempster-Shafer computational complexity scales with hypothesis set size**: Combination rule requires iterating over all subsets. For heuristic with 10 potential domains, 2^10 = 1024 subsets. Optimizations exist (focal elements), but implementation complexity high. May need to limit domain set size or use approximation. Requires prototyping to assess feasibility.

[blocker] **ADWIN memory usage for high-frequency validations**: ADWIN stores window of recent observations. High-validation-rate heuristics (100+ validations/day) may consume significant memory if monitoring individually. Solution: Aggregate to hourly success rate before feeding to ADWIN, or use fixed-window DDM for high-frequency cases.

[blocker] **Cold start problem for new heuristics**: No validation data → no confidence score, drift detection, or bandit reward. TrustRank seeding helps but requires manual golden rule curation. Potential solution: Transfer learning from similar heuristics (requires semantic similarity metric). Prototyping needed.

[blocker] **Defining "fraud" vs. "enthusiastic validation"**: User validates many heuristics quickly because they're genuinely helpful vs. botting. Isolation Forest flags both. Need labeled dataset of known fraud to tune contamination parameter and validate detection precision. CEO decision: Acceptable false positive rate?

---

### Questions

[question] **Should confidence scores be displayed with calibration metrics?** E.g., "85% confidence (±5% calibrated)" where calibration error quantifies historical accuracy. Increases transparency but may confuse users. Research shows calibration improves trust, but requires UI design consideration.

[question] **How to handle contradictory validations in same context?** User A: "This heuristic works for frontend testing" (success). User B: "This heuristic fails for frontend testing" (failure). Same domain, opposite outcomes. Options: (1) Store both with provenance (Wikidata approach), (2) Weight by validator reputation (Stack Overflow), (3) Flag for CEO review. What's the policy?

[question] **What is acceptable exploration rate for multi-armed bandit?** ε-greedy with ε=0.1 means 10% of recommendations are random exploration. Helps discover new heuristics but may frustrate users with irrelevant suggestions. Adaptive ε that decreases over time? Context-dependent (higher ε for experts who can handle experimentation)?

[question] **Should we implement vote fuzzing for confidence scores?** Reddit evidence: Effective deterrent, minimal cost. Concern: Reduces transparency, may be perceived as deceptive. Alternative: Display confidence ranges instead of point estimates (e.g., "0.75-0.85" instead of "0.80"). User preference testing needed.

[question] **How to seed initial trust for user-created heuristics (not derived from golden rules)?** Zero trust makes them invisible; default 0.5 trust may enable fraud. Probationary period with higher scrutiny? Require N validations from diverse sources before public visibility? Balance discoverability with fraud prevention.

[question] **Which domain hierarchy structure: user-defined tags vs. predefined taxonomy?** User tags (flexible, bottom-up) vs. predefined tree (structured, top-down). Wikidata uses user tags with conflicts; software often uses taxonomy (e.g., programming > python > django). Hybrid approach? Start with taxonomy, allow user extension?

[question] **Should drift detection trigger automatic confidence adjustment or just alerts?** ADWIN detects drift → automatically reduce confidence, or flag for manual review? Automation risk: False positives reduce valid heuristics. Manual review: Slower response to genuine context shifts. Hybrid: Auto-adjust with notification, allow override?

[question] **How to measure heuristic "success" for complex, multi-step tasks?** Binary success/failure is simple but loses nuance. Multi-dimensional (time saved, error reduction, user satisfaction)? Who rates success - the user who applied it, or external validators? Affects fraud detection (easier to game self-reported success).

---

## Conclusion

The research reveals a convergence of techniques across reputation systems, expert systems, and modern ML:

1. **Confidence modeling**: Dempster-Shafer theory provides the right abstraction for heuristic applicability
2. **Smoothing**: EWMA offers optimal simplicity and performance
3. **Fraud detection**: Multi-layered approach combining statistical, graph, and rate-based methods
4. **Adaptation**: ADWIN for drift detection, multi-armed bandits for selection
5. **Gaming prevention**: Diminishing returns, vote fuzzing, provenance tracking, TrustRank seeding

**Recommended architecture**: Hybrid system combining DS confidence + EWMA smoothing + Isolation Forest fraud detection + ADWIN drift monitoring + UCB bandit selection. Start simple (EWMA + Isolation Forest), add complexity incrementally as validation data accumulates.

**Next steps**: Prototype Dempster-Shafer combination rule, benchmark ADWIN on simulated heuristic trajectories, implement Isolation Forest on current dataset (if available), define fraud labeling criteria with CEO.

---

**Research completed by Agent 5**
**Total sources consulted: 50+**
**Estimated research depth: 40+ papers, systems, and libraries analyzed**

---

## Sources

### Expert Systems & Knowledge Bases
- [Dempster-Shafer Theory](https://www.brainkart.com/article/Dempster--Shafer-theory_8971/)
- [The Dempster-Shafer Theory of Evidence (ResearchGate)](https://www.researchgate.net/publication/242392452_The_Dempster-Shafer_theory_of_evidence)
- [Dempster-Shafer Theory by Glenn Shafer](https://glennshafer.com/assets/downloads/articles/article48.pdf)
- [The Dempster-Shafer Theory of Evidence - Chapter 13](https://www.shortliffe.net/Buchanan-Shortliffe-1984/Chapter-13.pdf)
- [Bayesian Networks for Expert Systems](https://link.springer.com/chapter/10.1007/978-3-642-11688-9_20)
- [NeurIPS 2024 Bayesian Decision-making Workshop](https://gp-seminar-series.github.io/neurips-2024/)

### Reputation Systems
- [Inside eBay's Real-Time Auction System](https://www.frugaltesting.com/blog/inside-ebays-real-time-auction-system-bidding-logic-algorithms-fraud-prevention-techniques)
- [eBay Acquires 3PM Shield](https://www.retaildive.com/news/ebay-acquires-3pm-shield-artificial-intelligence-fraud-detection/642699/)
- [Fraud Detection at eBay (2025)](https://www.sciencedirect.com/science/article/pii/S1566014125000263)
- [Reputation Gaming in Stack Overflow (ACM 2024)](https://dl.acm.org/doi/10.1145/3691627)
- [Stack Overflow Research Roadmap (Nov 2024)](https://stackoverflow.blog/2024/11/04/research-roadmap-update-november-2024/)
- [Reddit Karma Explained](https://karmatic.ai/how-does-reddit-karma-work-a-complete-guide-for-new-and-experienced-redditors/)
- [What is Reddit's Voting System?](https://dicloak.com/blog-detail/what-is-reddits-voting-system-heres-how-it-works)
- [Reddit Upvotes & Comment Karma (2025 Guide)](https://mediagrowth.io/reddit/reddit-upvotes-karma/)

### Anomaly Detection
- [Deep Learning for Time Series Anomaly Detection Survey (ACM 2024)](https://dl.acm.org/doi/10.1145/3691338)
- [Anomaly Detection in Multivariate Time Series (PMC 2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11156414/)
- [Machine Learning Approaches to Time Series Anomaly Detection](https://www.anomalo.com/blog/machine-learning-approaches-to-time-series-anomaly-detection/)
- [Dive into Time-Series Anomaly Detection: A Decade Review (arXiv 2024)](https://arxiv.org/abs/2412.20512)

### Trust & Confidence Scoring
- [Manipulability of PageRank under Sybil Strategies](https://www.researchgate.net/publication/200110773_Manipulability_of_PageRank_under_Sybil_Strategies)
- [Combating Web Spam with TrustRank](https://www.vldb.org/conf/2004/RS15P3.PDF)
- [SoK: The Evolution of Sybil Defense via Social Networks](https://www.cs.cornell.edu/lorenzo/papers/Alvisi13SoK.pdf)
- [Blockchain Sybil Attacks in 2024](https://mni.is/news_en/16220/blockchains-biggest-threat-how-new-defenses-are-crushing-sybil-attacks-in-2024/)
- [Modeling Public Trust in AI (Nature 2024)](https://www.nature.com/articles/s41598-025-23447-4)
- [Effects of Miscalibrated AI Confidence (arXiv 2024)](https://arxiv.org/html/2402.07632v4)
- [Machine Learning Models' Assessment: Trust and Performance (PMC 2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11485107/)
- [ACM Survey on Trust Evaluation Based on ML](https://dl.acm.org/doi/10.1145/3408292)

### Knowledge Graphs
- [Uncertainty Management in Knowledge Graph Construction (arXiv 2024)](https://arxiv.org/html/2405.16929v2)
- [Fact Checking Knowledge Graphs Survey (ACM 2024)](https://dl.acm.org/doi/10.1145/3749838)
- [Wikidata Conflicting Attributes](https://blog.gdeltproject.org/knowledge-graphs-over-wikidata-wikipedia-conflicting-attributes/)
- [Agreeing and Disagreeing in Wikidata (2023)](https://arxiv.org/html/2306.11766)

### Machine Learning
- [Multi-Armed Bandit for Concept Drift Adaptation (2024)](https://www.researchgate.net/publication/380597154_Multi-armed_bandit_based_online_model_selection_for_concept-drift_adaptation)
- [Non-Stationary Multi-Armed Bandit (PMC 2021)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8004723/)
- [Discovering State-of-the-Art RL Algorithms (Nature 2025)](https://www.nature.com/articles/s41586-025-09761-x)
- [RL-Based Hyper-Heuristics Review (PMC 2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11232579/)
- [Q-Learning Meta-Heuristic Algorithms (2024)](https://wires.onlinelibrary.wiley.com/doi/full/10.1002/widm.1548)
- [Concept Drift Detection Methods](https://www.aporia.com/learn/data-drift/concept-drift-detection-methods/)
- [Benchmarking Change Detector Algorithms (MDPI 2023)](https://www.mdpi.com/1999-5903/15/5/169)

### Python Libraries
- [PyOD 2: LLM-powered Model Selection (arXiv 2024)](https://arxiv.org/abs/2412.12154)
- [PyOD GitHub](https://github.com/yzhao062/pyod)
- [River (scikit-multiflow successor)](https://github.com/online-ml/river)
- [scikit-multiflow Documentation](https://scikit-multiflow.readthedocs.io/)
- [Exponential Smoothing for Time Series Forecasting](https://www.geeksforgeeks.org/artificial-intelligence/exponential-smoothing-for-time-series-forecasting/)
- [statsmodels Exponential Smoothing](https://www.statsmodels.org/dev/generated/statsmodels.tsa.holtwinters.SimpleExpSmoothing.html)
