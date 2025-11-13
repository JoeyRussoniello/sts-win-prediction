# **Slay the Spire — Run-Level Win Prediction (Project README)**

This project builds a full ML pipeline for predicting **win probability** in *Slay the Spire* using the public metrics dump containing tens of millions of runs. The core idea is simple: every run is a story of evolving decisions: cards taken, relics gained, paths chosen. Our pipeline aims to transform those stories into structured data that machine-learning models can learn from, and learn to give feedback on poor decisions during play.

## **Project Motivation**

Slay the Spire is uniquely suited for data-driven analysis:  

- every choice meaningfully changes the rest of the run  
- the rules are stable and deterministic  
- the dataset is enormous  
  
Understanding how deck composition, relic pathing, and floor-to-floor decisions shape victory lets us:

- quantify the real difficulty curve of each class  
- discover latent archetypes through embeddings  
- identify which strategic decisions correlate with success  
- build predictive models that understand run trajectory

## **Why This Project Is Different**

Despite the size and popularity of the Slay the Spire community, there is surprisingly **little rigorous research** on predicting run outcomes from *mid-run* information.  

Most previous ML attempts fall into two categories:

- **(1) Search-based agents that try to *play* the game**  
   Often built around Monte Carlo Tree Search or RL, these focus on *decision-making*, not understanding how real human runs evolve.

- **(2) Win prediction using the *final* deck or end-state summary**  
   These models cheat by relying on over-informative features (e.g., boss relics, act ending stats, final gold, floor number, or final deck composition).  
   They don't tell us *how* the run developed or which early decisions matter.

What’s missing is an analysis of the *actual* floor by floor, or card by card trajectory of a run. We aim to model win probability using realistic mid-run information that a player (or agent) would actually have.  

This project fills that gap by reconstructing complete run histories and building models that predict outcomes **long before the end-state is known**, giving genuine insight into strategy, archetype formation, and risk across the run.

## **Notebook Structure**

### **1) Processing**

We transform each nested JSON "run" into a **floor-by-floor dataset**, including:

- HP, gold, path type, and event outcomes  
- card picks, relic gains, shops, damage logs  
- reconstructed **deck state on every floor**  
- reconstructed **relic loadout**  
  
This produces a clean, rectangular dataset where each row is **one floor of one run**, ready for analysis and modeling.

### **2) Card Handling (Encoding & Embeddings)**

Decks contain hundreds of possible cards and upgrades, making encoding the central challenge of the project.  

We explore:

- **X-hot (one-hot with counts)** for exact card representation  
- **SVD embeddings** to compress decks into low-dimensional latent strategy vectors  
- (future) **learned embeddings** where models infer card relationships directly  

Early results show strong predictive signal in the SVD components, suggesting they capture meaningful archetype structure.

### **3) Exploratory Data Analysis (EDA)**

We visualize run distributions, class differences, and deck evolution across floors.  
Key insights so far:

- Deck size grows steadily but with class-specific patterns  
- Certain SVD components rise or fall predictably in winning runs  
- Relic count is strongly correlated with late-game survival  
- Floor-level HP curves differ sharply between victorious and losing runs  

EDA guides our modeling decisions and helps validate that the processed dataset behaves as expected.

## **Current Findings (So Far)**

- SVD components are consistently among the most predictive features  
- Ascension level is strongly monotonic with difficulty, as expected  
- Certain archetypes appear naturally in the embedding space  
- Early-floor decisions leave measurable signatures in final run outcome  
- Relic acquisition rate is a major driver of win probability  

These observations will be refined as we move into modeling and evaluation.

## **Next Steps**

- Train baseline models (Logistic Regression, Random Forest, Gradient Boosting)  
- Evaluate deck embeddings vs. raw card counts  
- Build per-floor win-probability curves  
- Experiment with neural models that learn card embeddings directly  

This README will be expanded once the modeling stage is complete.
