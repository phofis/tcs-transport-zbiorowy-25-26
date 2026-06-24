## 17.06
Cały projekt zacząłem od utworzenia dokładnej specyfikacji celów całego projektu. Pierwotnie projekt miał zakładać jedynie renderowanie pojazdów mpk w czasie rzeczywistym, jednak po ostatnich zajęciach zdecydowałem się uwzględnić również wyszukiwanie połączeń przy użyciu CSA, w prostym wariancie z optymalizacją tylko czasu dojazdu. Dopuszczam przejścia piesze, które zajmują maksymalnie 30 min.

Zdecydowałem się na użycie fastapi na backendzie, ponieważ chciałem nauczyć się tego frameworku, jest bardzo przydatny do bardzo szybkiego developmentu, więc będzie pasował do takiego małego zabawkowego projektu.

Specyfikację utworzyłem razem z Gemini, który podpowiedział użycie frontendowych bibliotek takich jak leaflet do renderowania map i markerów

## 24.06
Zacząłem od pisania frontendu, który jak narazie pokazuje mape zaczynając od centrum Krakowa, utworzyłem też boilerplate dla backendu, który narazie nic nie robi.

Dodałem renderowanie przystanków oraz pobieranie danych GTFS przez backend.

Dodałem renderowanie popupów, po kliknięciu w przystanek pojawia się jego tablica odjazdów

