```
Peripheral (CBPeripheral)
|-- uuid: UUID
|-- name: String?
|-- state: CBPeripheralState
|-- services: [CBService]?
    |-- Service (CBService)
        |-- uuid: CBUUID
        |-- isPrimary: Bool
        |-- characteristics: [CBCharacteristic]?
            |-- Characteristic (CBCharacteristic)
                |-- uuid: CBUUID
                |-- properties: CBCharacteristicProperties
                |-- value: Data?
                |-- isNotifying: Bool
                |-- descriptors: [CBDescriptor]?
                    |-- Descriptor (CBDescriptor)
                        |-- uuid: CBUUID
                        |-- value: Any?
                    |-- Descriptor (CBDescriptor)
                        |-- uuid: CBUUID
                        |-- value: Any?
            |-- Characteristic (CBCharacteristic)
                |-- ...
    |-- Service (CBService)
        |-- ...
```
