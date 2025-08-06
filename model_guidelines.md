# Aggiornamento 04-08
- Finire documentazione:
    - specificare tutti i problemi sui dati e scelte progettuali
    - motivo della dockerizzazione (QGIS)
    - aggiungere risultati
    - aggiungere visualizzazione dati, prima e dopo
- Finire GUI
- Nuovo modello con indici (UHEI)
- Nuovo dataset:
    - cambiare reti ferroviare
    - free space calcolato solo in 'Tessuto residenziale ..'
    - eliminare autostrade da aree stradali

# Aggiornamento 11-06
- Check docker
- Aggiornare i nomi delle features (json utili: final_grid, processed/aree_statistiche)
- Testare il modello su bologna full
- Check cambio di parametri
- Uniformare nomenclatura risultati, trovare un format da seguire
- Creare documentazione
- Finire Web GUI (leaflet) / Fare Powerpoint

# Aggiornamento 07-05
- parametrizzare e documentare al massimo il modello;
- creare read the docs;
- provare a creare un interfaccia web (in alternativa un semplice power point) in modo da mostrare varie configurazioni dei parametri, nella quale evidenziare l'utilità di ogni green cell, la densità di popolazione;
- aggiungere eventualmente altri parametri;
- accantonare l'idea della distribuzione (per ora);
- provare a considerare alberi e le fontane (cercare un dataset se esiste);
- provare ad escludere le piazze, es: +1000 m2 nel dataset delle strade;
- provare ad estendere a tutta Bologna, non solo al centro; magari andando poi a ragionare sul centro;
- next step -> indici di fragilità (ombra (?), multi-scala (?))
- (?) proporre eventualmente il confronto con diversi modelli di ML (?)

# Aggiornamento 10-05
dal dataset aree statistiche estrarre le aree vuote:
- areoporto
- via del vivaio
- lavino di mezzo
- rigosa
- san luca
- paderno
- san michele in bosco (?)
- osservanza (?)
- monte donato
- ponte savena-la bastia
- ospedale bellaria
- lungo savena
- croce del biacca
- stradelli guelfi
- scalo merci san donato 
- caab
- cadriano-calamosco
- savena abbandonato
- laghetti del rosario
- la noce
- tiro a segno
- caserme rosse-manifattura (?)
- fiera
- casteldebole
- villaggio delle barca

# Guida fattore di utilità
Impostare il modello nel modo seguente:
- Funzione obiettivo: massimizzare il fattore di utilità
- Pre-processing: calcorare il fattore di utilità prima dell'ottimizzazione in base a:
    - aree verdi già esistenti -> l'utilità scende
    - popolazione -> utilità sale
    - fattore ambientale (?)
    - ...
- Constraint: settare delle threshold che incrementano l'utilità di un fattore moltiplicativo quanto più l'area inserita è maggiore. L'incremento di utilità vale per la cella stessa e in maniera scalata per le celle circostanti.

- Constraint 28-04 (contintuità): inserire diminuzione fattore di utilità tanto più il numero di aree libere è elevato -> next step: terza dimensione in modo da tener conto non solo del numero di aree libere ma anche della dimensione di ciascun area 

# Aggiornamento 18-04
Improntare il modello sui seguenti punti:
1. Calcolare l'utilità a runtime
2. Si può costruire sia su strade che su cortili interni andado a considerare pesi diversi nell'influenza sul fattore di utilità:
    - **step 1:** porre la penalità come constraint sull'area verde massima edificabile (es: 0.3 * estensione_strada, 0.7 * estensione_cortile)
    - **step 2:** aggiungere anche un fattore penalizzante all'utilità di ognuno
3. esprimere il budget in termini di numero massimo di nuove aree verdi che inseriamo
4. Differenziare gli interventi e valutare effetti diversi sull'utilità: 
    - inserimento di nuove green cell interamente da zero -> utilità che segue i principi precedentemente menzionati
    - estensione di aree verdi esistenti -> scalare l'utilità del verde aggiunto in maniera esponenziale (o altro), in aggiunta ai fattori penalizzanti precedentemente menzionati.