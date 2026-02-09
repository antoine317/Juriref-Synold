
Présentation des fichiers :

Dans data/ sont présents :
- les données initiales (codes et jorf_2023_1990), 
- le rendu final dans data/html où tous les fichiers ont été convertis en html avec les hyperliens
    En passant la souris sur l'article, on aperçoit le code ou la loi à laquelle il est attaché
- Des données de calculs intermédiaires dans processed

Echec 1 et Echec 2 représentent mes tentatives infructueuses d'utiliser la méthode NER avec spacy (détail plus bas)

src contient :
- le fichier principal qui a servi à coder les regexps : generate_full_site
- debug.py, qui servait à ce que Copilot m'aide à débuger le code 
- 500lignes_hasard, fichier peu utile qui m'a servi à visualiser mes premières données aléatoirement

Tools contient : 
- Des outils pour ne simuler qu'une partie du code pour tester mes regexps

data_prep.py était une première étape pour récupérer les données depuis le format initial illisible


Points positifs :

Les regexp permettent bien d'attribuer le bon code à un article même si celui-ci est situé à un autre endroit de la phrase, ou que la phrase mentionne 2 codes différents
Les formats sont harmonisés (Art. 112 - 4 et article 112 quater renvoient la même référence)
Les codes sont systématiquement identifiés (bon, encore heureux !)
Les listes d'articles sont détectées

Limites principales :

Les lois les autres actes de la classe loi (décrets, convention) ne renvoient pas tout le temps vers une référence précise.
Cela était compliqué car elles ne sont pas toujours caractérisées par des chiffres donc on ne sait pas quand s'arrêter dans ce cas.
Ex : 
- "projet de loi de finances" renvoie à quelque chose de précis
- "loi créant ou modifiant des normes applicables aux collectivités territoriales et à leurs établissements publics" n'est pas une référence juridique précise
    Il est donc bien difficile de séparer ces cas par simples regexps

Les alinéas ne sont pas pris en compte dans le code. Je m'arrête aux articles et à leur première subdivision (après un tiret ou une lettre romaine)

Autres limites :

Les livres ne sont pas surlignés en tant que titres du html mais seulement lorsqu'ils sont cités dans le corps du texte.
Cela doit pouvoir se régler mais j'ai raté 2 fois de suite.



La question qui fâche : Pourquoi pas de NER ?
Pour être honnête, j'ai loupé le cours où le sujet était traité et je n'ai pas trop compris en regardant par moi-même.
J'ai mis du temps à comprendre qu'il fallait probablement que j'annote mes données à la main,
je codais quelques regexps sur une partie des textes et traitait le reste par NER mais les données d'entrainement étaient donc mauvaises.
J'ai ensuite essayé de créer un jeu de données annoté plusieurs fois par IA, mais sans me rendre compte que ce n'était pas déterministe non plus. 
Donc forcémenent le modèle entraîné par dessus était très mauvais mais je ne comprends pas pourquoi un LLM n'était pas capable de faire ce travail alors que j'essayais de lui donner des consignes précises.
En fait, cela revenait probablement à la même chose que quand je codais les regexps.
Je me suis rendu compte le dernier jour qu'il aurait fallu que je catégorise chaque mot à la main sur quelques centaines de lignes (si j'ai bien compris)


Bilan perso :

Depuis le début de ma scolarité, j'ai essayé de fuir le code car le début de 1A ne m'avait pas plu. J'ai juste fait un projet de computer vision très intéressant pour le trimestre Underwater.
J'ai choisi le cours de NLP pour essayer de comprendre un peu mieux le fonctionnement de l'IA vu les révolutions qu'elle amène, ce projet m'a beaucoup énervé car j'ai eu du mal mais je suis finalement content d'avoir réussi à me remettre un peu à coder !
Merci pour ce cours intéressant, j'y ai trouvé ce que je cherchais et il est bien organisé ! (il était compliqué pour les novices comme moi mais c'est normal de ne pas niveller les autres par le bas)
