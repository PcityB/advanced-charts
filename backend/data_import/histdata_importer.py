import os
import asyncio
import zipfile
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import asyncpg
from histdatacom import download_hist_data as dl
from config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HistDataImporter:
    """Import tick data from histdata.com into TimescaleDB"""
    
    SUPPORTED_PAIRS = [
        'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD',
        'USDCHF', 'NZDUSD', 'EURJPY', 'GBPJPY', 'EURGBP'
    ]
    
    TIMEFRAMES = {
        'tick': 'tick_data_last_quotes',
        'tick_bid_ask': 'tick_data_bid_ask',
        'M1': 'ascii',  # 1-minute bars
    }
    
    def __init__(self):
        self.download_dir = Path(settings.DATA_DOWNLOAD_DIR)
        self.extracted_dir = Path(settings.DATA_EXTRACTED_DIR)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.extracted_dir.mkdir(parents=True, exist_ok=True)
        
    async def download_data(
        self,
        pair: str,
        year: int,
        month: Optional[int] = None,
        timeframe: str = 'tick'
    ) -> Path:
        """
        Download historical data from histdata.com
        
        Args:
            pair: Currency pair (e.g., 'EURUSD')
            year: Year to download
            month: Optional month (1-12). If None, downloads entire year
            timeframe: 'tick', 'tick_bid_ask', or 'M1'
        
        Returns:
            Path to downloaded zip file
        """
        if pair not in self.SUPPORTED_PAIRS:
            raise ValueError(f"Pair {pair} not supported. Use one of {self.SUPPORTED_PAIRS}")
        
        if timeframe not in self.TIMEFRAMES:
            raise ValueError(f"Timeframe {timeframe} not supported. Use one of {list(self.TIMEFRAMES.keys())}")
        
        logger.info(f"Downloading {pair} data for {year}/{month or 'all'} - {timeframe}")
        
        try:
            # histdatacom uses sync downloads, run in executor
            loop = asyncio.get_event_loop()
            
            if month:
                filename = await loop.run_in_executor(
                    None,
                    dl,
                    pair,
                    year,
                    month,
                    self.TIMEFRAMES[timeframe],
                    str(self.download_dir)
                )
            else:
                # Download entire year month by month
                for m in range(1, 13):
                    try:
                        filename = await loop.run_in_executor(
                            None,
                            dl,
                            pair,
                            year,
                            m,
                            self.TIMEFRAMES[timeframe],
                            str(self.download_dir)
                        )
                        logger.info(f"Downloaded {pair} {year}/{m:02d}")
                    except Exception as e:
                        logger.error(f"Error downloading {pair} {year}/{m:02d}: {e}")
                        continue
            
            logger.info(f"Download completed")
            return self.download_dir
            
        except Exception as e:
            logger.error(f"Error downloading data: {e}")
            raise
    
    def extract_zip(self, zip_path: Path) -> Path:
        """Extract zip file to extracted directory"""
        logger.info(f"Extracting {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.extracted_dir)
        
        # Find the extracted CSV file
        csv_files = list(self.extracted_dir.glob('*.csv'))
        if not csv_files:
            raise FileNotFoundError("No CSV file found in extracted archive")
        
        return csv_files[0]
    
    async def parse_tick_data(self, csv_path: Path, symbol: str) -> List[tuple]:
        """
        Parse tick data CSV file
        
        Format: YYYYMMDD HHMMSS,Bid,Ask
        Example: 20240101 170003,1.10123,1.10125
        """
        logger.info(f"Parsing tick data from {csv_path}")
        records = []
        
        loop = asyncio.get_event_loop()
        
        def _parse():
            data = []
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 2:
                        continue
                    
                    try:
                        # Parse timestamp
                        timestamp_str = row[0]
                        dt = datetime.strptime(timestamp_str, '%Y%m%d %H%M%S')
                        
                        # Parse bid/ask
                        bid = float(row[1])
                        ask = float(row[2]) if len(row) > 2 else bid
                        
                        # Calculate volume (tick volume = 1 per tick)
                        volume = 1.0
                        
                        data.append((dt, symbol, bid, ask, volume))
                        
                    except Exception as e:
                        logger.warning(f"Error parsing row {row}: {e}")
                        continue
            
            return data
        
        records = await loop.run_in_executor(None, _parse)
        logger.info(f"Parsed {len(records)} tick records")
        return records
    
    async def parse_m1_data(self, csv_path: Path, symbol: str) -> List[tuple]:
        """
        Parse 1-minute bar data CSV file
        
        Format: YYYYMMDD HHMMSS,Open,High,Low,Close,Volume
        """
        logger.info(f"Parsing M1 data from {csv_path}")
        records = []
        
        loop = asyncio.get_event_loop()
        
        def _parse():
            data = []
            with open(csv_path, 'r') as f:
                reader = csv.reader(f, delimiter=';')  # Note: M1 uses semicolon
                for row in reader:
                    if len(row) < 6:
                        continue
                    
                    try:
                        # Parse timestamp
                        timestamp_str = row[0]
                        dt = datetime.strptime(timestamp_str, '%Y%m%d %H%M%S')
                        
                        # Parse OHLCV
                        open_price = float(row[1])
                        high = float(row[2])
                        low = float(row[3])
                        close = float(row[4])
                        volume = float(row[5])
                        
                        data.append((dt, symbol, 'M1', open_price, high, low, close, volume, 0))
                        
                    except Exception as e:
                        logger.warning(f"Error parsing row {row}: {e}")
                        continue
            
            return data
        
        records = await loop.run_in_executor(None, _parse)
        logger.info(f"Parsed {len(records)} M1 records")
        return records
    
    async def bulk_insert_ticks(self, records: List[tuple]):
        """Bulk insert tick data using asyncpg COPY"""
        if not records:
            logger.warning("No records to insert")
            return
        
        logger.info(f"Inserting {len(records)} tick records into database")
        
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        try:
            # Use COPY for high-performance bulk insert
            await conn.copy_records_to_table(
                'tick_data',
                records=records,
                columns=['time', 'symbol', 'bid', 'ask', 'volume']
            )
            logger.info("Tick data inserted successfully")
            
        except Exception as e:
            logger.error(f"Error inserting tick data: {e}")
            raise
        finally:
            await conn.close()
    
    async def bulk_insert_ohlcv(self, records: List[tuple]):
        """Bulk insert OHLCV data using asyncpg COPY"""
        if not records:
            logger.warning("No records to insert")
            return
        
        logger.info(f"Inserting {len(records)} OHLCV records into database")
        
        conn = await asyncpg.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            database=settings.DATABASE_NAME
        )
        
        try:
            await conn.copy_records_to_table(
                'ohlcv_data',
                records=records,
                columns=['time', 'symbol', 'timeframe', 'open', 'high', 'low', 'close', 'volume', 'tick_count']
            )
            logger.info("OHLCV data inserted successfully")
            
        except Exception as e:
            logger.error(f"Error inserting OHLCV data: {e}")
            raise
        finally:
            await conn.close()
    
    async def import_pair(
        self,
        pair: str,
        year: int,
        month: Optional[int] = None,
        timeframe: str = 'tick'
    ):
        """
        Complete import workflow: download, extract, parse, and insert
        
        Args:
            pair: Currency pair
            year: Year to import
            month: Optional specific month
            timeframe: 'tick', 'tick_bid_ask', or 'M1'
        """
        logger.info(f"Starting import for {pair} {year}/{month or 'all'}")
        
        # Download data
        await self.download_data(pair, year, month, timeframe)
        
        # Find and process all downloaded zip files
        zip_files = list(self.download_dir.glob(f"*{pair}*.zip"))
        logger.info(f"Found {len(zip_files)} zip files to process")
        
        for zip_file in zip_files:
            try:
                # Extract
                csv_path = self.extract_zip(zip_file)
                
                # Parse based on timeframe
                if timeframe in ['tick', 'tick_bid_ask']:
                    records = await self.parse_tick_data(csv_path, pair)
                    await self.bulk_insert_ticks(records)
                elif timeframe == 'M1':
                    records = await self.parse_m1_data(csv_path, pair)
                    await self.bulk_insert_ohlcv(records)
                
                # Cleanup
                csv_path.unlink()
                logger.info(f"Processed {zip_file.name}")
                
            except Exception as e:
                logger.error(f"Error processing {zip_file}: {e}")
                continue
        
        logger.info(f"Import completed for {pair}")
    
    async def import_date_range(
        self,
        pair: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = 'tick'
    ):
        """Import data for a date range"""
        current_date = start_date
        
        while current_date <= end_date:
            try:
                await self.import_pair(
                    pair,
                    current_date.year,
                    current_date.month,
                    timeframe
                )
            except Exception as e:
                logger.error(f"Error importing {current_date.year}/{current_date.month}: {e}")
            
            # Move to next month
            if current_date.month == 12:
                current_date = datetime(current_date.year + 1, 1, 1)
            else:
                current_date = datetime(current_date.year, current_date.month + 1, 1)


# CLI interface for data import
async def main():
    """Example usage"""
    importer = HistDataImporter()
    
    # Import EURUSD tick data for January 2024
    await importer.import_pair('EURUSD', 2024, 1, 'tick')
    
    # Or import a date range
    # start = datetime(2024, 1, 1)
    # end = datetime(2024, 3, 31)
    # await importer.import_date_range('EURUSD', start, end, 'tick')


if __name__ == "__main__":
    asyncio.run(main())
