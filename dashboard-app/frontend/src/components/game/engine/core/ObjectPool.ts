
export class ObjectPool<T> {
    private available: T[] = []
    private active: Set<T> = new Set()

    constructor(
        private factory: () => T,
        private reset: (obj: T) => void,
        initialSize: number = 0
    ) {
        for (let i = 0; i < initialSize; i++) {
            this.available.push(this.factory())
        }
    }

    acquire(): T {
        let obj = this.available.pop()
        if (!obj) {
            obj = this.factory()
        }

        this.reset(obj)
        this.active.add(obj)
        return obj
    }

    release(obj: T) {
        if (this.active.delete(obj)) {
            this.available.push(obj)
        }
    }

    forEach(callback: (obj: T) => void) {
        this.active.forEach(callback)
    }

    get activeCount() {
        return this.active.size
    }
}
