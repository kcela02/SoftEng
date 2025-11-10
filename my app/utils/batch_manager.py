"""
Batch Management System with FIFO Logic
Handles inventory batches, expiration tracking, and automatic FIFO stock deduction.
"""
from datetime import datetime, date, timedelta
from models import db, InventoryBatch, BatchTransaction, Product, Alert
from sqlalchemy import and_


class InsufficientStockError(Exception):
    """Raised when trying to deduct more stock than available."""
    pass


class BatchManager:
    """Manage inventory batches with FIFO logic and expiration tracking."""
    
    @staticmethod
    def add_batch(product_id, quantity, expiration_date, received_date=None, 
                  batch_number=None, unit_cost=None, supplier=None, notes=None, user_id=None):
        """
        Add a new inventory batch.
        
        Args:
            product_id: Product ID
            quantity: Number of units in batch
            expiration_date: Expiration date (date object or string YYYY-MM-DD)
            received_date: Date received (defaults to today)
            batch_number: Batch identifier (auto-generated if None)
            unit_cost: Cost per unit
            supplier: Supplier name
            notes: Additional notes
            user_id: User creating the batch
            
        Returns:
            InventoryBatch object
        """
        # Convert string dates to date objects
        if isinstance(expiration_date, str):
            expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d').date()
        
        if received_date is None:
            received_date = date.today()
        elif isinstance(received_date, str):
            received_date = datetime.strptime(received_date, '%Y-%m-%d').date()
        
        # Auto-generate batch number if not provided
        if batch_number is None:
            batch_number = BatchManager._generate_batch_number(product_id)
        
        # Check if batch is already expired
        is_expired = expiration_date < date.today()
        
        # Create batch
        batch = InventoryBatch(
            product_id=product_id,
            batch_number=batch_number,
            quantity=quantity,
            original_quantity=quantity,
            expiration_date=expiration_date,
            received_date=received_date,
            unit_cost=unit_cost,
            supplier=supplier,
            notes=notes,
            is_expired=is_expired
        )
        
        db.session.add(batch)
        db.session.flush()  # Get batch ID
        
        # Record transaction
        transaction = BatchTransaction(
            batch_id=batch.id,
            transaction_type='received',
            quantity_change=quantity,
            quantity_before=0,
            quantity_after=quantity,
            notes=f"Initial batch received: {batch_number}",
            user_id=user_id
        )
        db.session.add(transaction)
        
        # Update product total stock
        product = Product.query.get(product_id)
        if product:
            product.current_stock = (product.current_stock or 0) + quantity
        
        db.session.commit()
        
        # Create expiration alert if needed
        if batch.is_expiring_soon(threshold_days=7):
            BatchManager._create_expiration_alert(batch)
        
        return batch
    
    @staticmethod
    def deduct_stock_fifo(product_id, quantity_to_deduct, sale_id=None, user_id=None, notes=None):
        """
        Deduct stock using FIFO - oldest batches first (by expiration date).
        
        Args:
            product_id: Product ID
            quantity_to_deduct: Quantity to deduct
            sale_id: Optional sale ID for audit trail
            user_id: User performing the deduction
            notes: Optional notes
            
        Returns:
            List of deduction details: [{batch_id, batch_number, quantity_deducted, expiration_date}]
            
        Raises:
            InsufficientStockError: If not enough stock available
        """
        # Get all available batches for this product, ordered by expiration date (oldest first)
        batches = InventoryBatch.query.filter(
            InventoryBatch.product_id == product_id,
            InventoryBatch.quantity > 0,
            InventoryBatch.is_expired == False
        ).order_by(InventoryBatch.expiration_date.asc()).all()
        
        if not batches:
            raise InsufficientStockError(f"No stock available for product {product_id}")
        
        total_available = sum(b.quantity for b in batches)
        if total_available < quantity_to_deduct:
            raise InsufficientStockError(
                f"Insufficient stock. Requested: {quantity_to_deduct}, Available: {total_available}"
            )
        
        remaining_to_deduct = quantity_to_deduct
        deductions = []
        
        for batch in batches:
            if remaining_to_deduct <= 0:
                break
            
            # Calculate how much to deduct from this batch
            deducted = min(batch.quantity, remaining_to_deduct)
            quantity_before = batch.quantity
            
            # Update batch quantity
            batch.quantity -= deducted
            batch.updated_at = datetime.utcnow()
            remaining_to_deduct -= deducted
            
            # Record transaction
            transaction = BatchTransaction(
                batch_id=batch.id,
                sale_id=sale_id,
                transaction_type='sale',
                quantity_change=-deducted,
                quantity_before=quantity_before,
                quantity_after=batch.quantity,
                notes=notes or f"FIFO deduction for sale {sale_id}",
                user_id=user_id
            )
            db.session.add(transaction)
            
            # Track deduction details
            deductions.append({
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'quantity_deducted': deducted,
                'expiration_date': batch.expiration_date.isoformat(),
                'days_until_expiry': batch.days_until_expiry(),
                'unit_cost': batch.unit_cost
            })
        
        # Update product total stock
        product = Product.query.get(product_id)
        if product:
            product.current_stock = (product.current_stock or 0) - quantity_to_deduct
        
        db.session.commit()
        
        return deductions
    
    @staticmethod
    def get_product_batches(product_id, include_empty=False, include_expired=False):
        """
        Get all batches for a product.
        
        Args:
            product_id: Product ID
            include_empty: Include batches with 0 quantity
            include_expired: Include expired batches
            
        Returns:
            List of InventoryBatch objects ordered by expiration date
        """
        query = InventoryBatch.query.filter_by(product_id=product_id)
        
        if not include_empty:
            query = query.filter(InventoryBatch.quantity > 0)
        
        if not include_expired:
            query = query.filter(InventoryBatch.is_expired == False)
        
        return query.order_by(InventoryBatch.expiration_date.asc()).all()
    
    @staticmethod
    def check_expiring_batches(days_threshold=7, product_id=None):
        """
        Find batches expiring within threshold days.
        
        Args:
            days_threshold: Number of days to look ahead
            product_id: Optional product ID to filter
            
        Returns:
            List of expiring batch details
        """
        threshold_date = date.today() + timedelta(days=days_threshold)
        
        query = InventoryBatch.query.filter(
            InventoryBatch.quantity > 0,
            InventoryBatch.expiration_date <= threshold_date,
            InventoryBatch.expiration_date >= date.today(),
            InventoryBatch.is_expired == False
        )
        
        if product_id:
            query = query.filter_by(product_id=product_id)
        
        expiring = query.order_by(InventoryBatch.expiration_date.asc()).all()
        
        alerts = []
        for batch in expiring:
            days_until_expiry = batch.days_until_expiry()
            urgency = batch.urgency_level()
            
            alerts.append({
                'batch_id': batch.id,
                'product_id': batch.product_id,
                'product_name': batch.product.name,
                'batch_number': batch.batch_number,
                'quantity': batch.quantity,
                'expiration_date': batch.expiration_date.isoformat(),
                'days_until_expiry': days_until_expiry,
                'urgency': urgency,
                'unit_cost': batch.unit_cost,
                'potential_loss': (batch.quantity * batch.unit_cost) if batch.unit_cost else None
            })
        
        return alerts
    
    @staticmethod
    def mark_expired_batches():
        """
        Mark batches that have passed their expiration date.
        Creates alerts for expired stock.
        
        Returns:
            Number of batches marked as expired
        """
        today = date.today()
        
        expired_batches = InventoryBatch.query.filter(
            InventoryBatch.expiration_date < today,
            InventoryBatch.is_expired == False,
            InventoryBatch.quantity > 0
        ).all()
        
        count = 0
        for batch in expired_batches:
            batch.is_expired = True
            batch.updated_at = datetime.utcnow()
            
            # Create alert for expired stock
            alert = Alert(
                product_id=batch.product_id,
                alert_type='batch_expired',
                severity='CRITICAL',
                message=f"Batch {batch.batch_number} has expired with {batch.quantity} units remaining",
                is_active=True
            )
            db.session.add(alert)
            
            # Record transaction
            transaction = BatchTransaction(
                batch_id=batch.id,
                transaction_type='expired',
                quantity_change=0,
                quantity_before=batch.quantity,
                quantity_after=batch.quantity,
                notes=f"Batch marked as expired on {today}"
            )
            db.session.add(transaction)
            
            count += 1
        
        db.session.commit()
        return count
    
    @staticmethod
    def get_batch_cost_breakdown(product_id):
        """
        Get cost breakdown by batch for a product (for COGS calculation).
        
        Args:
            product_id: Product ID
            
        Returns:
            List of batch cost information
        """
        batches = InventoryBatch.query.filter(
            InventoryBatch.product_id == product_id,
            InventoryBatch.quantity > 0,
            InventoryBatch.is_expired == False
        ).order_by(InventoryBatch.expiration_date.asc()).all()
        
        breakdown = []
        total_quantity = 0
        total_value = 0
        
        for batch in batches:
            value = (batch.quantity * batch.unit_cost) if batch.unit_cost else 0
            total_quantity += batch.quantity
            total_value += value
            
            breakdown.append({
                'batch_number': batch.batch_number,
                'quantity': batch.quantity,
                'unit_cost': batch.unit_cost,
                'total_value': value,
                'expiration_date': batch.expiration_date.isoformat(),
                'received_date': batch.received_date.isoformat()
            })
        
        avg_cost = total_value / total_quantity if total_quantity > 0 else 0
        
        return {
            'batches': breakdown,
            'total_quantity': total_quantity,
            'total_value': total_value,
            'average_cost': avg_cost
        }
    
    @staticmethod
    def adjust_batch_quantity(batch_id, quantity_change, reason, user_id=None):
        """
        Manually adjust batch quantity (for corrections, damage, etc.).
        
        Args:
            batch_id: Batch ID
            quantity_change: Change in quantity (positive or negative)
            reason: Reason for adjustment
            user_id: User making adjustment
            
        Returns:
            Updated batch
        """
        batch = InventoryBatch.query.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        quantity_before = batch.quantity
        new_quantity = batch.quantity + quantity_change
        
        if new_quantity < 0:
            raise ValueError(f"Cannot reduce quantity below 0. Current: {batch.quantity}, Change: {quantity_change}")
        
        batch.quantity = new_quantity
        batch.updated_at = datetime.utcnow()
        
        # Update product total stock
        product = Product.query.get(batch.product_id)
        if product:
            product.current_stock = (product.current_stock or 0) + quantity_change
        
        # Record transaction
        transaction = BatchTransaction(
            batch_id=batch_id,
            transaction_type='adjustment',
            quantity_change=quantity_change,
            quantity_before=quantity_before,
            quantity_after=new_quantity,
            notes=reason,
            user_id=user_id
        )
        db.session.add(transaction)
        db.session.commit()
        
        return batch
    
    @staticmethod
    def _generate_batch_number(product_id):
        """Generate unique batch number."""
        today = date.today()
        prefix = f"BATCH-{today.strftime('%Y%m%d')}"
        
        # Count existing batches for today
        count = InventoryBatch.query.filter(
            InventoryBatch.product_id == product_id,
            InventoryBatch.batch_number.like(f"{prefix}%")
        ).count()
        
        return f"{prefix}-P{product_id:03d}-{count+1:03d}"
    
    @staticmethod
    def _create_expiration_alert(batch):
        """Create alert for expiring batch."""
        days = batch.days_until_expiry()
        urgency = batch.urgency_level()
        
        if urgency in ['CRITICAL', 'HIGH']:
            message = f"Batch {batch.batch_number} expires in {days} days ({batch.quantity} units)"
            
            # Check if alert already exists
            existing = Alert.query.filter(
                Alert.product_id == batch.product_id,
                Alert.alert_type == 'batch_expiring',
                Alert.is_active == True,
                Alert.message.contains(batch.batch_number)
            ).first()
            
            if not existing:
                alert = Alert(
                    product_id=batch.product_id,
                    alert_type='batch_expiring',
                    severity=urgency,
                    message=message,
                    is_active=True
                )
                db.session.add(alert)
                db.session.commit()
