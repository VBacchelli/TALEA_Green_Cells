# Guida fattore di utilità
Impostare il modello nel modo seguente:
- Funzione obiettivo: massimizzare il fattore di utilità
- Pre-processing: calcorare il fattore di utilità prima dell'ottimizzazione in base a:
    - aree verdi già esistenti -> l'utilità scende
    - popolazione -> utilità sale
    - fattore ambientale (?)
    - ...
- Constraint: settare delle threshold che incrementano l'utilità di un fattore moltiplicativo quanto più l'area inserita è maggiore. L'incremento di utilità vale per la cella stessa e in maniera scalata per le celle circostanti.