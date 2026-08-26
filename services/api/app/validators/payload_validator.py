from typing import Dict, Any, List
from..models.operation import ValidationError

class PayloadValidator:
    @staticmethod
    def validate_product_upload(payload: Dict[str, Any], operation_id:int) -> List[ValidationError]:
        errors = []
        products = payload.get("products", [])

        if not products:
            errors.append(ValidationError(
                operation_id=operation_id,
                row_number=None,
                field_name="products",
                error_code="EMPTY_PRODUCTS",
                error_message="Список товаров пуст"
            ))
            return errors


        for idx, product in enumerate(products, start=1):
            if "id" not in product:
                errors.append(ValidationError(
                    operation_id=operation_id,
                    row_number=idx,
                    field_name='id',
                    error_code='REQUIRED_FIELD',
                    error_message=f'В строке {idx} отсутствует обязательное поле id'
                ))

            if 'name' not in product or not product.get('name'):
                errors.append(ValidationError(
                    operation_id=operation_id,
                    row_number=idx,
                    field_name='name',
                    error_code='REQUIRED_FIELD',
                    error_message=f'В строке {idx} отсутствует обязательное поле name'
                ))

            if 'price' in product:
                try:
                    price= float(product['price'])
                    if price < 0:
                        errors.append(ValidationError(
                            operation_id=operation_id,
                            row_number=idx,
                            field_name='price',
                            error_code='INVALID_VALUE',
                            error_message=f'В строке {idx} цена не может быть отрицательной: {price}'
                        ))
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        operation_id=operation_id,
                        row_number=idx,
                        field_name='price',
                        error_code='INVALID_FORMAT',
                        error_message=f'В строке {idx} поле price должно быть числом'
                    ))
        return errors

    @staticmethod
    def validate_price_update(payload: Dict[str, Any], operation_id: int) -> List[ValidationError]:
        errors = []
        updates = payload.get('updates', [])

        if not updates:
            errors.append(ValidationError(
                operation_id=operation_id,
                row_number=None,
                field_name='updates',
                error_code='EMPTY_UPDATES',
                error_message='Список обновлений пуст'
            ))
            return errors

        for idx, update in enumerate(updates, start=1):
            if 'product_id' not in update:
                errors.append(ValidationError(
                    operation_id=operation_id,
                    row_number=idx,
                    field_name='product_id',
                    error_code='REQUIRED_FIELD',
                    error_message=f'В строке {idx} отсутствует обязательное поле product_id',
                ))

            if 'new_price' in update:
                try:
                    price = float(update['new_price'])
                    if price < 0:
                        errors.append(ValidationError(
                            operation_id=operation_id,
                            row_number=idx,
                            field_name='new_price',
                            error_code='INVALID_VALUE',
                            error_message = f'В строке {idx} цена не может быть отрицательной: {price}'
                        ))
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        operation_id=operation_id,
                        row_number=idx,
                        field_name='new_price',
                        error_code='INVALID_FORMAT',
                        error_message = f'В строке {idx} поле new_price должно быть числом',
                    ))
        return errors

    @staticmethod
    def validate_stock_update(payload: Dict[str, Any], operation_id: int) -> List[ValidationError]:
        errors = []
        items = payload.get('items', [])

        if not items:
            errors.append(ValidationError(
                operation_id=operation_id,
                row_number=None,
                field_name='items',
                error_code='EMPTY_ITEMS',
                error_message='Список товаров для обновления остатков пуст'
            ))
            return errors

        for idx, item in enumerate(items, start=1):
            if 'product_id' not in item:
                errors.append(ValidationError(
                    operation_id=operation_id,
                    row_number=idx,
                    field_name='product_id',
                    error_code='REQUIRED_FIELD',
                    error_message=f'В строке {idx} отсутствует обязательное поле product_id'
                ))

            if 'quantity' in item:
                try:
                    qty = int(item['quantity'])
                    if qty < 0:
                        errors.append(ValidationError(
                            operation_id=operation_id,
                            row_number=idx,
                            field_name='quantity',
                            error_code='INVALID_VALUE',
                            error_message=f'В строке {idx} количество не может быть отрицательный: {qty}'
                        ))
                except (ValueError, TypeError):
                    errors.append(ValidationError(
                        operation_id=operation_id,
                        row_number=idx,
                        field_name='quantity',
                        error_code='INVALID_FORMAT',
                        error_message=f'В строке {idx} поле quantity должно быть целым числом'
                    ))
        return errors

    @staticmethod
    def validate(payload: Dict[str, Any], operation_type: str, operation_id: int) -> List[ValidationError]:
        validators = {
            'product_upload': PayloadValidator.validate_product_upload,
            'price_update': PayloadValidator.validate_price_update,
            'stock_update': PayloadValidator.validate_stock_update,
        }

        validator = validators.get(operation_type)
        if not validator:
            return [ValidationError(
                operation_id=operation_id,
                row_number=None,
                field_name='operation_type',
                error_code='UNKNOWN_OPERATION_TYPE',
                error_message=f'Неизвестный тип операции: {operation_type}'
            )]
        return validator(payload, operation_id)

