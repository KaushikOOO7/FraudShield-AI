package com.fraudshield.app.core.db

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase
import kotlinx.coroutines.flow.Flow

@Entity(tableName = "history_case")
data class HistoryCaseEntity(
    @PrimaryKey val caseId: String,
    val serializedCase: String,
    val type: String?,
    val createdAt: String?,
    val receivedAt: Long,
    val demo: Boolean,
)

@Entity(tableName = "report_outbox")
data class ReportOutboxEntity(
    @PrimaryKey val localId: String,
    val serializedRequest: String,
    val createdAt: String,
    val attempts: Int = 0,
)

@Entity(tableName = "entity_cache")
data class EntityCacheEntity(
    @PrimaryKey val entity: String,
    val serializedCase: String,
    val expiresAt: Long,
)

@Entity(tableName = "settings")
data class SettingEntity(@PrimaryKey val key: String, val value: String)

@Dao
interface HistoryDao {
    @Query("DELETE FROM history_case WHERE caseId = :id AND demo = :demo")
    suspend fun delete(id: String, demo: Boolean)
    @Query("SELECT * FROM history_case WHERE demo = :demo ORDER BY receivedAt DESC")
    fun observe(demo: Boolean): Flow<List<HistoryCaseEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(items: List<HistoryCaseEntity>)

    @Query("SELECT * FROM history_case WHERE caseId = :id AND demo = :demo LIMIT 1")
    suspend fun find(id: String, demo: Boolean): HistoryCaseEntity?

    @Query("DELETE FROM history_case")
    suspend fun clear()
}

@Dao
interface SettingsDao {
    @Query("SELECT * FROM settings")
    fun observe(): Flow<List<SettingEntity>>

    @Query("SELECT value FROM settings WHERE `key` = :key LIMIT 1")
    suspend fun get(key: String): String?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun put(setting: SettingEntity)
}

@Dao
interface OutboxDao {
    @Query("SELECT * FROM report_outbox ORDER BY createdAt")
    fun observe(): Flow<List<ReportOutboxEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun enqueue(item: ReportOutboxEntity)

    @Query("DELETE FROM report_outbox WHERE localId = :id")
    suspend fun remove(id: String)
}

@Dao
interface EntityCacheDao {
    @Query("SELECT * FROM entity_cache WHERE entity = :entity AND expiresAt > :now LIMIT 1")
    suspend fun find(entity: String, now: Long): EntityCacheEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(item: EntityCacheEntity)
}

@Database(
    entities = [HistoryCaseEntity::class, ReportOutboxEntity::class, EntityCacheEntity::class, SettingEntity::class],
    version = 1,
    exportSchema = false,
)
abstract class FraudShieldDatabase : RoomDatabase() {
    abstract fun historyDao(): HistoryDao
    abstract fun settingsDao(): SettingsDao
    abstract fun outboxDao(): OutboxDao
    abstract fun entityCacheDao(): EntityCacheDao
}
