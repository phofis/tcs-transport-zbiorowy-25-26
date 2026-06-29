Przed przeczytaniem podsumowania polecam pobieżnie przejść przez ``README.md``

## Planowanie (Piotr)
Cały projekt rozpoczęliśmy od zaplanowania pełnego pipeline'u konwertowania danych z ``.osm.pbf`` do formatu, który będzie najkorzystniejszy pod względem szybkości preprocessingu. Zdecydowaliśmy się na tablice offsetów i krawędzi (jak na wykładzie) z AoS, ponieważ oba pola (wierzchołek końcowy krawędzi i waga) będą wykorzystywane ze sobą w Dijkstrze. Do partycjonowania grafu skorzystaliśmy z podziału METIS i biblioteki udostępnionej na githubie (wspomniana na wykładzie).

## Pipeline (Piotr)
Pliki pobrane z OpenStreetMap na początku były pozbawiane wszystkich obiektów innych niż ``highway`` za pomocą CLI Osmium.
``osmium tags-filter malopolskie-latest.osm.pbf nw/highway -o malopolskie.osm.pbf``
Rozmiar pliku zmniejszał się ~4x.

Zredukowany plik trafiał do skrytu ``osm2txt.py``, który generował tablice offsetów i krawędzi, w formacie ``txt`` dla debugu lub domyślnie ``bin`` dla szybszego wczytywania.

Na podstawie tych danych, generowaliśmy kolejny plik, tym razem z partycją grafu, za pomocą ``partition_main.cpp``, testowaliśmy 32, 64 i 128 regionów.

Zbierając wszystkie poprzednie pliki z danymi mogliśmy wygenerować flagi za pomocą ``preprocess.cpp`` i ``preprocess_thread.cpp`` (wersja CUDA została zabugowana, o tym będzie dalej).

Mając tablice offsetów i krawędzi, partycje oraz flagi wykonujemy query za pomocą ``query.cpp``.

Cały pipeline możemy aktywować z ``Makefile``.

## Preprocessing (Szymon)

## Benchmark (Piotr)

- `preprocess`, `preprocess_thread` (OpenMP)
- Mierzyliśmy jedynie samo przeliczanie arc-flags `arcFlagsPreprocessing()` używając `std::chrono::steady_clock`
- Regiony R: 32, 64, 128
- Liczba wątków: 1 (basic), 4, 16 

### Graph sizes

- **malopolskie**: N=2,014,633, M=4,009,829
- **poland**: N=17,173,642, M=34,062,059
- **germany**: N=35,291,139, M=70,603,808

## Wyniki

- **maloppolskie R=32**: basic=262s, t4=68s (3.9x), t16=28s (9.2x)
- **maloppolskie R=64**: basic=427s, t4=110s (3.9x), t16=39s (10.8x)
- **maloppolskie R=128**: basic=699s, t4=178s (3.9x), t16=46s (15.0x)
- **poland R=32**: basic=7652s, t4=2279s (3.4x), t16=538s (14.2x)
- **poland R=64**: basic=12969s, t4=3671s (3.5x), t16=905s (14.3x)
- **poland R=128**: basic=20615s, t4=5469s (3.8x), t16=1496s (13.8x)
- **germany R=32**: basic=31179s, t4=8764s (3.6x), t16=2213s (14.1x)
- **germany R=64**: basic=48650s, t4=15185s (3.2x), t16=3407s (14.3x)
- **germany R=128**: basic=75945s, t4=22903s (3.3x), t16=5196s (14.6x)