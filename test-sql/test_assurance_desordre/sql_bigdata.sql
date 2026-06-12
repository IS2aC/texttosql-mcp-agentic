-- ============================================================
--  BASE DE TEST : test_assurance_desordre (VERSION VOLUMINEUSE)
--  Simule un système d'assurance avec mauvaise gouvernance BD
--  + génération de données massives (100 000+ lignes) pour
--  tester les performances de la plateforme.
-- ============================================================

-- Nettoyage propre si re-exécution
DROP TABLE IF EXISTS audit_log       CASCADE;
DROP TABLE IF EXISTS data_paiements  CASCADE;
DROP TABLE IF EXISTS sinistres_tbl   CASCADE;
DROP TABLE IF EXISTS contrats        CASCADE;
DROP TABLE IF EXISTS produits_assurance CASCADE;
DROP TABLE IF EXISTS clients_v2      CASCADE;
DROP TABLE IF EXISTS tbl_experts     CASCADE;
DROP TABLE IF EXISTS table_a         CASCADE;

-- ┌─────────────────────────────────────────────────────────┐
-- │  1. TABLE_A  →  Agences                                 │
-- └─────────────────────────────────────────────────────────┘
CREATE TABLE table_a (
    id_agence       SERIAL PRIMARY KEY,
    NOM_AGENCE      VARCHAR(100) NOT NULL,
    ville           varchar(80),
    Code_Region     CHAR(3),
    tel             VARCHAR(20),
    Email_Contact   VARCHAR(120),
    DateCreation    DATE,
    actif           SMALLINT DEFAULT 1
);

-- ┌─────────────────────────────────────────────────────────┐
-- │  2. TBL_EXPERTS  →  Experts sinistres                   │
-- └─────────────────────────────────────────────────────────┘
CREATE TABLE tbl_experts (
    expertID        SERIAL PRIMARY KEY,
    nom_complet     VARCHAR(120) NOT NULL,
    specialite      VARCHAR(80),
    tel_expert      VARCHAR(20),
    zone_geo        CHAR(3),
    disponible      BOOLEAN DEFAULT TRUE
);

-- ┌─────────────────────────────────────────────────────────┐
-- │  3. CLIENTS_V2  →  Assurés                              │
-- └─────────────────────────────────────────────────────────┘
CREATE TABLE clients_v2 (
    CLIENT_ID       SERIAL PRIMARY KEY,
    prenom          VARCHAR(60),
    NOM             VARCHAR(60) NOT NULL,
    date_naissance  DATE,
    Sexe            CHAR(1),
    num_tel         VARCHAR(25),
    email           VARCHAR(120),
    adresse         TEXT,
    code_postal     VARCHAR(10),
    VILLE           VARCHAR(80),
    id_agence_fk    INT REFERENCES table_a(id_agence),
    date_adhesion   TIMESTAMP,
    statut_client   VARCHAR(20) DEFAULT 'actif'
);

-- ┌─────────────────────────────────────────────────────────┐
-- │  4. PRODUITS_ASSURANCE  →  Produits / Garanties         │
-- └─────────────────────────────────────────────────────────┘
CREATE TABLE produits_assurance (
    prod_id         SERIAL PRIMARY KEY,
    libelle         VARCHAR(150) NOT NULL,
    TYPE_PRODUIT    VARCHAR(50),
    prime_mensuelle NUMERIC(10,2),
    prime_annuelle  NUMERIC(10,4),
    franchise       NUMERIC(8,2) DEFAULT 0,
    actif           CHAR(1) DEFAULT 'O',
    code_produit    VARCHAR(15) UNIQUE
);

-- ┌─────────────────────────────────────────────────────────┐
-- │  5. CONTRATS  →  Contrats souscrits                     │
-- └─────────────────────────────────────────────────────────┘
CREATE TABLE contrats (
    NumContrat      VARCHAR(20) PRIMARY KEY,
    client_id       INT REFERENCES clients_v2(CLIENT_ID),
    PROD_ID         INT REFERENCES produits_assurance(prod_id),
    date_debut      DATE NOT NULL,
    date_fin        DATE,
    montant_prime   NUMERIC(10,2),
    statut          VARCHAR(15),
    agence_souscription INT REFERENCES table_a(id_agence),
    commentaire     TEXT,
    dateCreation    TIMESTAMP DEFAULT NOW()
);

-- ┌─────────────────────────────────────────────────────────┐
-- │  6. SINISTRES_TBL  →  Sinistres déclarés                │
-- └─────────────────────────────────────────────────────────┘
CREATE TABLE sinistres_tbl (
    SIN_ID            SERIAL PRIMARY KEY,
    num_contrat       VARCHAR(20) REFERENCES contrats(NumContrat),
    Date_Sinistre     DATE NOT NULL,
    description       TEXT,
    montant_estime    NUMERIC(12,2),
    montant_rembourse NUMERIC(12,4),
    statut_sin        VARCHAR(20),
    expert_id         INT,              -- volontairement sans FK vers tbl_experts
    date_cloture      DATE
);

-- ┌─────────────────────────────────────────────────────────┐
-- │  7. DATA_PAIEMENTS  →  Paiements de primes              │
-- └─────────────────────────────────────────────────────────┘
CREATE TABLE data_paiements (
    paiement_id        BIGSERIAL PRIMARY KEY,
    NumContrat         VARCHAR(20) REFERENCES contrats(NumContrat),
    montant_paye       NUMERIC(10,2),
    DATE_PAIEMENT      TIMESTAMP NOT NULL,
    mode_paiement      VARCHAR(30),
    reference_paiement VARCHAR(50),
    statut_paie        CHAR(1)
);

-- ┌─────────────────────────────────────────────────────────┐
-- │  8. AUDIT_LOG  →  Historique des modifications          │
-- └─────────────────────────────────────────────────────────┘
CREATE TABLE audit_log (
    log_id     BIGSERIAL PRIMARY KEY,
    table_name VARCHAR(60),
    operation  VARCHAR(10),
    user_db    VARCHAR(60) DEFAULT current_user,
    ts         TIMESTAMP DEFAULT NOW(),
    old_data   TEXT,
    new_data   TEXT
);


-- ============================================================
--  DONNÉES DE RÉFÉRENCE (petites tables, données fixes)
-- ============================================================

-- Agences (20 agences réparties sur plusieurs régions)
INSERT INTO table_a (NOM_AGENCE, ville, Code_Region, tel, Email_Contact, DateCreation, actif)
SELECT
    'Agence ' || v.nom,
    v.ville,
    v.region,
    CASE WHEN random() < 0.85
         THEN '+225 27 ' || lpad((20 + (g % 70))::text, 2, '0') || ' ' ||
              lpad((10 + (g % 89))::text, 2, '0') || ' ' ||
              lpad((10 + (g % 89))::text, 2, '0') || ' ' ||
              lpad((10 + (g % 89))::text, 2, '0')
         ELSE NULL END,
    lower(replace(v.nom, ' ', '')) || '@assur.ci',
    (DATE '2005-01-01' + (g * 137) * INTERVAL '1 day')::date,
    CASE WHEN random() < 0.92 THEN 1 ELSE 0 END
FROM (
    SELECT g,
           (ARRAY['Centrale Abidjan','Nord','Sud','Est','Ouest','Cocody','Yopougon','Marcory',
                  'Treichville','Adjamé','Bouaké Centre','San-Pédro Port','Daloa',
                  'Korhogo','Abengourou','Man','Gagnoa','Divo','Bondoukou','Soubré'])[g] AS nom,
           (ARRAY['Abidjan','Abidjan','San-Pédro','Abengourou','Abidjan','Abidjan','Abidjan','Abidjan',
                  'Abidjan','Abidjan','Bouaké','San-Pédro','Daloa',
                  'Korhogo','Abengourou','Man','Gagnoa','Divo','Bondoukou','Soubré'])[g] AS ville,
           (ARRAY['ABJ','BKE','SPN','ABG','ABJ','ABJ','ABJ','ABJ',
                  'ABJ','ABJ','BKE','SPN','DAL',
                  'KOR','ABG','MAN','GAG','DIV','BON','SOU'])[g] AS region
    FROM generate_series(1, 20) AS g
) v;

-- Experts (50 experts)
INSERT INTO tbl_experts (nom_complet, specialite, tel_expert, zone_geo, disponible)
SELECT
    (ARRAY['Konan','Traoré','Yves','Aminata','Kouassi','Bamba','Ouattara','Diabaté',
           'N''Guessan','Coulibaly','Yao','Koné','Diallo','Gnagne','Kouadio'])[1 + (g % 15)]
        || ' ' ||
    (ARRAY['Brou','Aminata','Mensah','Stéphane','Pascal','Awa','Fatou','Jean',
           'Issouf','Marie','Paul','Brice','Sandra','Olivier','Carine'])[1 + (g % 15)],
    (ARRAY['Auto','Habitation','auto','SANTE','Vie','Incendie','Transport'])[1 + (g % 7)],
    '+225 0' || (1 + (g % 9)) || ' ' ||
        lpad((10 + (g % 89))::text, 2, '0') || ' ' ||
        lpad((10 + (g % 89))::text, 2, '0') || ' ' ||
        lpad((10 + (g % 89))::text, 2, '0'),
    (ARRAY['ABJ','BKE','SPN','ABG','DAL','KOR','MAN'])[1 + (g % 7)],
    random() < 0.75
FROM generate_series(1, 50) AS g;

-- Produits (catalogue fixe, comme dans la version d'origine + variantes)
INSERT INTO produits_assurance (libelle, TYPE_PRODUIT, prime_mensuelle, prime_annuelle, franchise, actif, code_produit) VALUES
('Assurance Auto Tiers Simple',     'Auto',       8500.00,   98000.0000, 50000.00, 'O', 'AUTO-TIERS-01'),
('Assurance Auto Tous Risques',     'auto',      22000.00,  250000.0000, 20000.00, 'O', 'AUTO-TR-01'),
('Multirisque Habitation Confort',  'Habitation', 5500.00,   63000.0000, 15000.00, 'O', 'HAB-CONF-01'),
('Assurance Vie Épargne Plus',      'Vie',       15000.00,  175000.0000,     0.00, 'O', 'VIE-EP-01'),
('Assurance Santé Senior',          'SANTE',     12000.00,  138000.0000, 10000.00, 'N', 'SAN-SEN-01'),
('Assurance Auto Jeune Conducteur', 'Auto',      18000.00,  205000.0000, 30000.00, 'O', 'AUTO-JC-01'),
('Multirisque Habitation Essentiel','habitation', 3200.00,   38000.0000, 10000.00, 'O', 'HAB-ESS-01'),
('Assurance Santé Famille',         'Sante',     20000.00,  230000.0000, 15000.00, 'O', 'SAN-FAM-01'),
('Assurance Vie Temporaire',        'vie',        9000.00,  104000.0000,     0.00, 'O', 'VIE-TMP-01'),
('Assurance Transport Marchandises','Transport', 30000.00,  340000.0000, 50000.00, 'O', 'TRANS-MARCH-01');


-- ============================================================
--  DONNÉES VOLUMINEUSES (100 000+ lignes par table)
--  NB : seq.set_config est utilisé pour accélérer generate_series
-- ============================================================

-- ┌─────────────────────────────────────────────────────────┐
-- │  CLIENTS_V2  →  150 000 assurés                          │
-- └─────────────────────────────────────────────────────────┘
INSERT INTO clients_v2 (prenom, NOM, date_naissance, Sexe, num_tel, email, adresse, code_postal, VILLE, id_agence_fk, date_adhesion, statut_client)
SELECT
    (ARRAY['Kouadio','Adjoua','Moussa','Fatou','Jean-Paul','Aya','Konan','Awa','Issouf','Marie',
           'Yao','Aminata','Brice','Sandra','Olivier','Carine','Paul','Mariam','Serge','Nadège'])[1 + (g % 20)],
    upper((ARRAY['Yao','Koffi','Coulibaly','Diallo','Gnagne','Kone','Traore','Ouattara','Bamba','Diabate',
                  'Toure','Kouassi','Brou','Kamagate','Sanogo','Kouame','Zadi','Tape','Adou','Soro'])[1 + (g % 20)]),
    (DATE '1955-01-01' + ((g * 37) % 25000) * INTERVAL '1 day')::date,
    CASE (g % 5)
        WHEN 0 THEN 'M'
        WHEN 1 THEN 'F'
        WHEN 2 THEN 'm'
        WHEN 3 THEN 'f'
        ELSE 'M'
    END,
    CASE WHEN g % 11 = 0 THEN NULL
         ELSE '+225 0' || (1 + (g % 9)) || ' ' ||
              lpad((10 + (g % 89))::text, 2, '0') || ' ' ||
              lpad((10 + ((g*3) % 89))::text, 2, '0') || ' ' ||
              lpad((10 + ((g*7) % 89))::text, 2, '0')
    END,
    CASE WHEN g % 7 = 0 THEN NULL
         ELSE 'client' || g || '@mail.com'
    END,
    'Quartier ' || (ARRAY['Cocody','Yopougon','Marcory','Treichville','Adjamé','Plateau','Koumassi',
                           'Riviera','Abobo','Port-Bouët'])[1 + (g % 10)] || ', Lot ' || (g % 999),
    CASE WHEN g % 13 = 0 THEN NULL
         ELSE lpad(((g % 99) + 1)::text, 2, '0') || '00' || ((g % 9) + 1)::text
    END,
    (ARRAY['Abidjan','ABIDJAN','abidjan','Bouaké','San-Pédro','Daloa','Korhogo','Abengourou','Man','Gagnoa'])[1 + (g % 10)],
    1 + (g % 20),
    (TIMESTAMP '2010-01-01 08:00:00' + (g % 5800) * INTERVAL '1 day' + (g % 24) * INTERVAL '1 hour'),
    CASE (g % 9)
        WHEN 0 THEN 'inactif'
        WHEN 1 THEN 'ACTIF'
        WHEN 2 THEN 'Actif'
        WHEN 3 THEN 'suspendu'
        ELSE 'actif'
    END
FROM generate_series(1, 150000) AS g;


-- ┌─────────────────────────────────────────────────────────┐
-- │  CONTRATS  →  150 000 contrats (1 par client environ)    │
-- └─────────────────────────────────────────────────────────┘
INSERT INTO contrats (NumContrat, client_id, PROD_ID, date_debut, date_fin, montant_prime, statut, agence_souscription, commentaire, dateCreation)
SELECT
    'CTR-' || (2010 + (g % 16))::text || '-' || lpad(g::text, 7, '0'),
    g,                                            -- client_id = g (1..150000)
    1 + (g % 10),                                 -- PROD_ID 1..10
    (DATE '2010-01-01' + (g % 5800) * INTERVAL '1 day')::date,
    CASE WHEN g % 6 = 0 THEN NULL
         ELSE (DATE '2010-01-01' + (g % 5800) * INTERVAL '1 day' + INTERVAL '5 years')::date
    END,
    (3000 + (g % 28000))::numeric(10,2),
    CASE (g % 10)
        WHEN 0 THEN 'résilié'
        WHEN 1 THEN 'ACTIF'
        WHEN 2 THEN 'Actif'
        WHEN 3 THEN 'suspendu'
        ELSE 'actif'
    END,
    1 + (g % 20),
    CASE WHEN g % 17 = 0 THEN 'Renouvellement automatique'
         WHEN g % 23 = 0 THEN 'En attente régularisation'
         ELSE NULL
    END,
    (TIMESTAMP '2010-01-01 00:00:00' + (g % 5800) * INTERVAL '1 day')
FROM generate_series(1, 150000) AS g;


-- ┌─────────────────────────────────────────────────────────┐
-- │  SINISTRES_TBL  →  120 000 sinistres                     │
-- │  (certains contrats ont plusieurs sinistres, d'autres 0) │
-- └─────────────────────────────────────────────────────────┘
INSERT INTO sinistres_tbl (num_contrat, Date_Sinistre, description, montant_estime, montant_rembourse, statut_sin, expert_id, date_cloture)
SELECT
    'CTR-' || (2010 + (((g * 7) % 150000 + 1) % 16))::text || '-' || lpad((((g * 7) % 150000) + 1)::text, 7, '0'),
    (DATE '2015-01-01' + (g % 4000) * INTERVAL '1 day')::date,
    (ARRAY[
        'Collision frontale — parking centre-ville',
        'Bris de glace + rayures capot',
        'Dégât des eaux — cuisine inondée',
        'Vol accessoires intérieur véhicule',
        'Incendie cuisine — départ de feu maîtrisé',
        'Choc arrière en stationnement',
        'Inondation sous-sol après fortes pluies',
        'Bris de vitre - cambriolage',
        'Accident corporel - tiers impliqué',
        'Dommages tempête - toiture endommagée'
    ])[1 + (g % 10)],
    (10000 + (g % 490000))::numeric(12,2),
    CASE WHEN g % 8 = 0 THEN 0
         ELSE ((10000 + (g % 490000)) * (0.5 + (g % 5) * 0.1))::numeric(12,4)
    END,
    CASE (g % 6)
        WHEN 0 THEN 'ouvert'
        WHEN 1 THEN 'OUVERT'
        WHEN 2 THEN 'Clôturé'
        WHEN 3 THEN 'cloturé'
        WHEN 4 THEN 'en_cours'
        ELSE 'ouvert'
    END,
    CASE WHEN g % 9 = 0 THEN NULL ELSE 1 + (g % 50) END,
    CASE WHEN g % 4 = 0 THEN NULL
         ELSE (DATE '2015-01-01' + (g % 4000) * INTERVAL '1 day' + (10 + (g % 90)) * INTERVAL '1 day')::date
    END
FROM generate_series(1, 120000) AS g;


-- ┌─────────────────────────────────────────────────────────┐
-- │  DATA_PAIEMENTS  →  300 000 paiements                    │
-- │  (en moyenne 2 paiements par contrat)                    │
-- └─────────────────────────────────────────────────────────┘
INSERT INTO data_paiements (NumContrat, montant_paye, DATE_PAIEMENT, mode_paiement, reference_paiement, statut_paie)
SELECT
    'CTR-' || (2010 + (((g % 150000) + 1) % 16))::text || '-' || lpad(((g % 150000) + 1)::text, 7, '0'),
    (3000 + (g % 28000))::numeric(10,2),
    (TIMESTAMP '2010-01-01 00:00:00' + (g % 5800) * INTERVAL '1 day' + (g % 24) * INTERVAL '1 hour'),
    (ARRAY['virement','VIREMENT','Virement','CB','cb','Carte','carte bancaire','espèces','Espèces','mobile money'])[1 + (g % 10)],
    'REF' || (2010 + (g % 16))::text || lpad(g::text, 8, '0'),
    CASE (g % 12)
        WHEN 0 THEN 'R'
        WHEN 1 THEN 'P'
        ELSE 'V'
    END
FROM generate_series(1, 300000) AS g;


-- ┌─────────────────────────────────────────────────────────┐
-- │  AUDIT_LOG  →  100 000 entrées (bruit applicatif)        │
-- └─────────────────────────────────────────────────────────┘
INSERT INTO audit_log (table_name, operation, user_db, ts, old_data, new_data)
SELECT
    (ARRAY['clients_v2','contrats','sinistres_tbl','data_paiements','produits_assurance','table_a'])[1 + (g % 6)],
    (ARRAY['INSERT','UPDATE','DELETE','insert','update'])[1 + (g % 5)],
    (ARRAY['app_user','etl_job','admin','migration_script','api_service'])[1 + (g % 5)],
    (TIMESTAMP '2018-01-01 00:00:00' + (g % 3000) * INTERVAL '1 day' + (g % 86400) * INTERVAL '1 second'),
    CASE WHEN g % 3 = 0 THEN '{"statut":"actif"}' ELSE NULL END,
    CASE WHEN g % 3 = 0 THEN '{"statut":"suspendu"}' ELSE '{"id":' || g || '}' END
FROM generate_series(1, 100000) AS g;


-- ============================================================
--  INDEX UTILES (optionnel mais recommandé sur gros volumes)
-- ============================================================
CREATE INDEX idx_clients_v2_agence       ON clients_v2(id_agence_fk);
CREATE INDEX idx_contrats_client         ON contrats(client_id);
CREATE INDEX idx_contrats_produit        ON contrats(PROD_ID);
CREATE INDEX idx_contrats_agence         ON contrats(agence_souscription);
CREATE INDEX idx_sinistres_num_contrat   ON sinistres_tbl(num_contrat);
CREATE INDEX idx_paiements_num_contrat   ON data_paiements(NumContrat);
CREATE INDEX idx_audit_log_table_name    ON audit_log(table_name);


-- ============================================================
--  CONTRÔLE RAPIDE DES VOLUMES
-- ============================================================
SELECT 'table_a'            AS table_name, COUNT(*) FROM table_a
UNION ALL
SELECT 'tbl_experts',                      COUNT(*) FROM tbl_experts
UNION ALL
SELECT 'clients_v2',                       COUNT(*) FROM clients_v2
UNION ALL
SELECT 'produits_assurance',               COUNT(*) FROM produits_assurance
UNION ALL
SELECT 'contrats',                         COUNT(*) FROM contrats
UNION ALL
SELECT 'sinistres_tbl',                    COUNT(*) FROM sinistres_tbl
UNION ALL
SELECT 'data_paiements',                   COUNT(*) FROM data_paiements
UNION ALL
SELECT 'audit_log',                        COUNT(*) FROM audit_log;