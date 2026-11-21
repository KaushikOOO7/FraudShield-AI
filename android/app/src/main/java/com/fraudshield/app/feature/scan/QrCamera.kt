package com.fraudshield.app.feature.scan

import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

@androidx.annotation.OptIn(markerClass=[androidx.camera.core.ExperimentalGetImage::class])
@Composable internal fun QrCamera(modifier:Modifier,onFound:(String)->Unit,onError:()->Unit){
    val context=LocalContext.current;val owner=LocalLifecycleOwner.current
    val previewView=remember(context){PreviewView(context)}
    val found by rememberUpdatedState(onFound);val errorCallback by rememberUpdatedState(onError)
    AndroidView(factory={previewView},modifier=modifier)
    DisposableEffect(context,owner){
        val live=AtomicBoolean(true);val delivered=AtomicBoolean(false)
        val executor=Executors.newSingleThreadExecutor();val scanner=BarcodeScanning.getClient()
        val future=ProcessCameraProvider.getInstance(context)
        val preview=Preview.Builder().build().apply{setSurfaceProvider(previewView.surfaceProvider)}
        val analysis=ImageAnalysis.Builder().setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST).build()
        analysis.setAnalyzer(executor){proxy->
            val image=proxy.image
            if(image==null||!live.get()||delivered.get())proxy.close()
            else scanner.process(InputImage.fromMediaImage(image,proxy.imageInfo.rotationDegrees))
                .addOnSuccessListener{codes->codes.firstNotNullOfOrNull{it.rawValue}?.takeIf{it.length<=4000}?.let{value->if(live.get()&&delivered.compareAndSet(false,true))found(value)}}
                .addOnFailureListener{failure->android.util.Log.w("FraudShield","QR decode failed: ${failure.javaClass.simpleName}");if(live.get())errorCallback()}
                .addOnCompleteListener{proxy.close()}
        }
        future.addListener({if(live.get())try{future.get().bindToLifecycle(owner,CameraSelector.DEFAULT_BACK_CAMERA,preview,analysis)}
            catch(failure:java.util.concurrent.ExecutionException){android.util.Log.w("FraudShield","Camera provider failed");errorCallback()}
            catch(failure:IllegalArgumentException){android.util.Log.w("FraudShield","Camera unavailable");errorCallback()}
            catch(failure:SecurityException){android.util.Log.w("FraudShield","Camera permission revoked");errorCallback()}
        },ContextCompat.getMainExecutor(context))
        onDispose{live.set(false);analysis.clearAnalyzer();if(future.isDone)try{future.get().unbind(preview,analysis)}catch(failure:java.util.concurrent.ExecutionException){android.util.Log.w("FraudShield","Camera disposal failed")}
            scanner.close();executor.shutdown()}
    }
}
