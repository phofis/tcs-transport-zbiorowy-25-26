## 17.06
Cały projekt zacząłem od utworzenia dokładnej specyfikacji celów całego projektu. Pierwotnie projekt miał zakładać jedynie renderowanie pojazdów mpk w czasie rzeczywistym, jednak po ostatnich zajęciach zdecydowałem się uwzględnić również wyszukiwanie połączeń przy użyciu CSA, w prostym wariancie z optymalizacją tylko czasu dojazdu. Dopuszczam przejścia piesze, które zajmują maksymalnie 30 min.

Zdecydowałem się na użycie fastapi na backendzie, ponieważ chciałem nauczyć się tego frameworku, jest bardzo przydatny do bardzo szybkiego developmentu, więc będzie pasował do takiego małego zabawkowego projektu.

Specyfikację utworzyłem razem z Gemini, który podpowiedział użycie frontendowych bibliotek takich jak leaflet do renderowania map i markerów

## 24.06
Zacząłem od pisania frontendu, który jak narazie pokazuje mape zaczynając od centrum Krakowa, utworzyłem też boilerplate dla backendu, który narazie nic nie robi.

Dodałem renderowanie przystanków oraz pobieranie danych GTFS przez backend.

Dodałem renderowanie popupów, po kliknięciu w przystanek pojawia się jego tablica odjazdów

Dodałem renderowanie pojazdów w czasie rzeczywistym. Strona działa zauważalnie wolniej, przeciąganie myszką po mapie ma opóźnienie, a do tego, sporo pojazdów 'skacze' po ekranie całkowicie zmieniając swoją pozycje (pokonanie tak dużych odcinków nie jest możliwe w rzeczywistości w tak krótkich odstępach czasu), jak narazie nie doszukałem się buga po swojej stronie, narazie zostawiam z połowicznym rozwiązaniem i nie animuję tych pojazdów jeśli przeniosły ponad X metrów w jednej aktualizacji.

Część pojazdów czasem znika, też nie wiem z jakiego powodu :(

## 25.06

Po długiej walce z bugami niestety dalej nic nie zdziałałem, niektóre pojazdy nadal losowo pojawiają się i znikają, próbowałem różnych rozwiązań i dochodzę do wniosku, że te znikające pojazdy pojawiają się gdzieś całkowicie indziej (według danych gtfs) i przez to, że nie animuje ich 'przeniesienia', wyglądają jakby znikały.

Zająłem się implementacją CSA, nie zajęło długo ponieważ konstruowanie bloków Connections, na których wykonywane są query, już miałem napisane, ponieważ były wykorzystywane przy feedach odjazdów na poszczególnych przystankach.

Zdecydowałem się na 1 pokazaną, prostą implementację odtwarzania podróży w postaci zapisywania znaczników "z jakiego znacznika najszybciej dojedziemy na obecny".
Trzymam w pamięci connections, które "odbędą" się w najbliższych ~72h w blokach po 4h.
Background worker dba o wyrzucanie przedawnionionych bloków i tworzenie nowych.

Dodałem możliwość wyboru customowych punktów startu i końca podróży, za pomocą ustawiania markerów na mapie. Dynamicznie obliczają trasy piesze do przystanków, teraz ta wyszukiwarka naprawdę nabiera sensu :)

Doszlifowałem trochę UI, trasa na mapie nie jest już 3 długimi prostymi odcinkami, teraz mamy odcinki między pośredniemi przystankami.

