-- ============================================================
--  BASE DE TEST : test_assurance_desordre
--  Simule un système d'assurance avec mauvaise gouvernance BD
--  Ordre de création respecté pour DBeaver / pgAdmin
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
--  DONNÉES DE TEST
-- ============================================================

-- Agences
INSERT INTO table_a (NOM_AGENCE, ville, Code_Region, tel, Email_Contact, DateCreation, actif) VALUES
('Agence Centrale Abidjan',  'Abidjan',    'ABJ', '+225 27 20 30 40 50', 'centrale@assur.ci',  '2010-03-15', 1),
('agence nord',              'Bouaké',     'BKE', '+225 27 31 00 11 22', 'nord@assur.ci',      '2013-07-01', 1),
('AGENCE SUD',               'San-Pédro',  'SPN', NULL,                  'sud@assur.ci',       '2015-11-20', 1),
('Agence Est',               'Abengourou', 'ABG', '+225 27 44 55 66 77', NULL,                 '2018-02-10', 0);

-- Experts
INSERT INTO tbl_experts (nom_complet, specialite, tel_expert, zone_geo, disponible) VALUES
('Konan Brou Stéphane', 'Auto',       '+225 07 55 66 77', 'ABJ', TRUE),
('Traoré Aminata',      'Habitation', '+225 05 33 44 55', 'BKE', TRUE),
('Yves Mensah',         'auto',       '+225 01 99 00 11', 'ABJ', FALSE);

-- Assurés
INSERT INTO clients_v2 (prenom, NOM, date_naissance, Sexe, num_tel, email, adresse, code_postal, VILLE, id_agence_fk, date_adhesion, statut_client) VALUES
('Kouadio',   'YAO',       '1985-04-12', 'M', '+225 07 11 22 33', 'k.yao@mail.com',       '12 Rue des Cocotiers', '00225', 'Abidjan',    1, '2020-01-10 08:00:00', 'actif'),
('Adjoua',    'KOFFI',     '1990-09-25', 'f', '+225 05 44 55 66', 'adjoua.k@mail.com',    '45 Bd Lagunaire',      '00225', 'ABIDJAN',    1, '2019-06-15 09:30:00', 'ACTIF'),
('Moussa',    'COULIBALY', '1978-12-03', 'M', NULL,               'mcoulibaly@ymail.com', 'Quartier Commerce',    '01400', 'Bouaké',     2, '2021-03-22 00:00:00', 'actif'),
('Fatou',     'DIALLO',    '1995-07-18', 'F', '+225 01 77 88 99', NULL,                   'Résidence Les Palmes', '18300', 'San-Pédro',  3, '2022-08-05 14:00:00', 'inactif'),
('Jean-Paul', 'GNAGNE',    '1982-02-28', 'm', '+225 07 22 33 44', 'jp.gnagne@corp.ci',    'Zone Industrielle K7', '00225', 'abidjan',    1, '2018-11-30 10:15:00', 'actif');

-- Produits
INSERT INTO produits_assurance (libelle, TYPE_PRODUIT, prime_mensuelle, prime_annuelle, franchise, actif, code_produit) VALUES
('Assurance Auto Tiers Simple',    'Auto',       8500.00,   98000.0000, 50000.00, 'O', 'AUTO-TIERS-01'),
('Assurance Auto Tous Risques',    'auto',      22000.00,  250000.0000, 20000.00, 'O', 'AUTO-TR-01'),
('Multirisque Habitation Confort', 'Habitation', 5500.00,   63000.0000, 15000.00, 'O', 'HAB-CONF-01'),
('Assurance Vie Épargne Plus',     'Vie',       15000.00,  175000.0000,     0.00, 'O', 'VIE-EP-01'),
('Assurance Santé Senior',         'SANTE',     12000.00,  138000.0000, 10000.00, 'N', 'SAN-SEN-01');

-- Contrats
INSERT INTO contrats (NumContrat, client_id, PROD_ID, date_debut, date_fin, montant_prime, statut, agence_souscription, commentaire) VALUES
('CTR-2020-0001', 1, 1, '2020-01-10', '2025-01-10', 8500.00,  'actif',    1, NULL),
('CTR-2019-0047', 2, 3, '2019-06-15', '2024-06-15', 5500.00,  'ACTIF',    1, 'Renouvellement automatique'),
('CTR-2021-0103', 3, 2, '2021-03-22', '2026-03-22', 22000.00, 'actif',    2, NULL),
('CTR-2022-0215', 4, 4, '2022-08-05', NULL,         15000.00, 'suspendu', 3, 'En attente régularisation'),
('CTR-2018-0008', 5, 1, '2018-11-30', '2023-11-30', 8500.00,  'résilié',  1, 'Résiliation à échéance');

-- Sinistres
INSERT INTO sinistres_tbl (num_contrat, Date_Sinistre, description, montant_estime, montant_rembourse, statut_sin, expert_id) VALUES
('CTR-2020-0001', '2022-03-14', 'Collision frontale — parking centre-ville',  350000.00, 280000.0000, 'ouvert',  1),
('CTR-2021-0103', '2023-07-02', 'Bris de glace + rayures capot',               85000.00,  85000.0000, 'Clôturé', 1),
('CTR-2019-0047', '2021-11-18', 'Dégât des eaux — cuisine inondée',           120000.00,  95000.0000, 'OUVERT',  2),
('CTR-2020-0001', '2024-01-09', 'Vol accessoires intérieur véhicule',          45000.00,      0.0000, 'ouvert',  NULL);

-- Paiements
INSERT INTO data_paiements (NumContrat, montant_paye, DATE_PAIEMENT, mode_paiement, reference_paiement, statut_paie) VALUES
('CTR-2020-0001', 8500.00,  '2020-01-10 08:05:00', 'virement', 'VIR202001100001', 'V'),
('CTR-2020-0001', 8500.00,  '2020-02-10 09:00:00', 'CB',       'CB20200210KY01',  'V'),
('CTR-2019-0047', 5500.00,  '2019-06-15 10:00:00', 'Carte',    'CART201906AK',    'V'),
('CTR-2021-0103', 22000.00, '2021-03-22 00:00:00', 'VIREMENT', 'VIR202103MC001',  'V'),
('CTR-2022-0215', 15000.00, '2022-08-05 14:10:00', 'cb',       'CB20220805FD',    'P'),
('CTR-2018-0008', 8500.00,  '2018-11-30 10:20:00', 'virement', 'VIR201811JP001',  'R');