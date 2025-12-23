-- MARA: General Material Data
CREATE COLUMN TABLE "MARA" (
    "MATNR" NVARCHAR(18) PRIMARY KEY, -- Material Number [cite: 138, 258]
    "MTART" NVARCHAR(4),              -- Material Type
    "MBRSH" NVARCHAR(1),              -- Industry Sector
    "MEINS" NVARCHAR(3),              -- Base Unit of Measure
    "MAKTX" NVARCHAR(40)              -- Material Description
);

-- KNA1: General Data in Customer Master
CREATE COLUMN TABLE "KNA1" (
    "KUNNR" NVARCHAR(10) PRIMARY KEY, -- Customer Number [cite: 138, 258]
    "NAME1" NVARCHAR(35),             -- Name [cite: 19]
    "ORT01" NVARCHAR(35),             -- City [cite: 22, 417]
    "PSTLZ" NVARCHAR(10),             -- Postal Code [cite: 24, 394]
    "LAND1" NVARCHAR(3),              -- Country Key [cite: 428]
    "TELF1" NVARCHAR(16),             -- First Telephone Number [cite: 24, 718]
    "ERDAT" DATE                      -- Created On [cite: 206]
);

-- VBAK: Sales Document: Header Data
CREATE COLUMN TABLE "VBAK" (
    "VBELN" NVARCHAR(10) PRIMARY KEY, -- Sales Document [cite: 138, 258]
    "KUNNR" NVARCHAR(10),             -- Customer Number
    "ERDAT" DATE,                     -- Created on Date [cite: 206]
    "AUART" NVARCHAR(4),              -- Sales Document Type
    "NETWR" DECIMAL(15, 2),           -- Net Value in Document Currency [cite: 176]
    "WAERK" NVARCHAR(5),              -- SD Document Currency [cite: 2043]
    "VKORG" NVARCHAR(4),              -- Sales Organization
    FOREIGN KEY ("KUNNR") REFERENCES "KNA1"("KUNNR")
);

-- VBAP: Sales Document: Item Data
CREATE COLUMN TABLE "VBAP" (
    "VBELN" NVARCHAR(10),             -- Sales Document [cite: 258]
    "POSNR" NVARCHAR(6),              -- Sales Document Item
    "MATNR" NVARCHAR(18),             -- Material Number
    "KWMENG" DECIMAL(15, 3),          -- Cumulative Order Quantity
    "NETPR" DECIMAL(11, 2),           -- Net Price
    "WAERK" NVARCHAR(5),              -- Document Currency
    PRIMARY KEY ("VBELN", "POSNR"),
    FOREIGN KEY ("VBELN") REFERENCES "VBAK"("VBELN"),
    FOREIGN KEY ("MATNR") REFERENCES "MARA"("MATNR")
);

-- BKPF: Accounting Document Header
CREATE COLUMN TABLE "BKPF" (
    "BUKRS" NVARCHAR(4),              -- Company Code
    "BELNR" NVARCHAR(10),             -- Accounting Document Number [cite: 258]
    "GJAHR" NVARCHAR(4),              -- Fiscal Year
    "BLART" NVARCHAR(2),              -- Document Type
    "BLDAT" DATE,                     -- Document Date [cite: 206]
    "MONAT" NVARCHAR(2),              -- Fiscal Period
    "USNAM" NVARCHAR(12),             -- User Name [cite: 732]
    PRIMARY KEY ("BUKRS", "BELNR", "GJAHR")
);

-- BSEG: Accounting Document Segment
CREATE COLUMN TABLE "BSEG" (
    "BUKRS" NVARCHAR(4),              -- Company Code
    "BELNR" NVARCHAR(10),             -- Accounting Document Number
    "GJAHR" NVARCHAR(4),              -- Fiscal Year
    "BUZEI" NVARCHAR(3),              -- Number of Line Item Within Accounting Document [cite: 258]
    "BSCHL" NVARCHAR(2),              -- Posting Key
    "KOART" NVARCHAR(1),              -- Account Type
    "WRBTR" DECIMAL(13, 2),           -- Amount in Document Currency [cite: 176]
    PRIMARY KEY ("BUKRS", "BELNR", "GJAHR", "BUZEI"),
    FOREIGN KEY ("BUKRS", "BELNR", "GJAHR") REFERENCES "BKPF"("BUKRS", "BELNR", "GJAHR")
);