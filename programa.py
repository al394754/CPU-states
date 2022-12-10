from ast import Str
from glob import escape
import sys
from typing import *

def read_data(f) -> List[Str]:
    listado: List[Str] = f.readlines()
    return listado

def procesar_datos(listado: List[Str]):
    cores: int = int(listado[1].strip().rsplit("=")[1])
    wbase: float = float(listado[3].strip().rsplit("=")[1])
    wcoreinactivo: float = float(listado[5].strip().rsplit("=")[1])
    coreC: float = float(listado[7].strip().rsplit("=")[1])
    frecuencias: List[float] = []
    for frecuencia in listado[9].strip().rsplit("=")[1].split(";"):
        frecuencias.append(float(frecuencia))
    voltajes: List[float] = []
    for voltaje in listado[11].strip().rsplit("=")[1].split(";"):
        voltajes.append(float(voltaje))
    cant_partes: int = (len(listado) - 12) / 9
    return cores, wbase, wcoreinactivo, coreC, frecuencias, voltajes, cant_partes

def procesar_partes(listado: List[Str], parte: int):
    #12 líneas base + 9 líneas por parte
    num_linea = 12 + 9 * parte
    tiempo_secuencial: float = float(listado[num_linea + 2].strip().rsplit("=")[1])
    pestado: int = int(listado[num_linea + 4].strip().rsplit("=")[1])
    grado_paralelizacion: int = int(listado[num_linea + 6].strip().rsplit("=")[1])
    division_trabajo: List[int] = []
    for division in listado[num_linea + 8].strip().rsplit("=")[1].split("; "):
        division_trabajo.append(int(division))
    return tiempo_secuencial, pestado, grado_paralelizacion, division_trabajo

def calcula_tiempo(estados: List[int], tiempo_secuencial: float, grado_paralelizacion: int, division_trabajo: List[float]):
    tiempos_iniciales: List[float] = []
    for i in range(grado_paralelizacion):
        tiempos_iniciales.append(float(format((tiempo_secuencial * division_trabajo[i] / 100), ".2f")))
    tiempos: List[float] = []
    for i in range(grado_paralelizacion):
        tiempo = frecuencias[0] / frecuencias[estados[i]] * tiempos_iniciales[i]
        tiempos.append(tiempo)
    return tiempos    

def arreglar_tiempos(tiempos: List[float]):
    tiempos_nuevos: List[float] = []
    for i in range(len(tiempos)):
        tiempos[i] = round(tiempos[i], 6)
        ultimo_dig = int(repr(tiempos[i])[-1]) 
        if(ultimo_dig == 5):
            tiempos[i] += 0.001 #esto es porque el round cuando acaba en 5 tiende al par, por lo que .365 irá hacia .360 antes que .670
        tiempos[i] = round(tiempos[i], 6)
        tiempos_nuevos.append(tiempos[i])
    return tiempos_nuevos

def calcula_potencia(coreC: float, frecuencias: List[float], voltajes: List[float]): #Calcula cada potencia activa de los estados posibles 
    potencias: List[float] = []
    for ind in range(len(voltajes)):
        potencias.append(round((1.2 + coreC * frecuencias[ind] * voltajes[ind]**2), 6))
    return potencias

def process(cores: int, wbase: float, wcoreinactivo: float, coreC: float, frecuencias: List[float], voltajes: List[float], tiempo_secuencial: float, pestado: int, grado_paralelizacion: int, division_trabajo: List[int], parte: int):
    estados_por_consumo: List[int] = [] #estados ordenados por consumo según el tiempo de ejecución
    minimo_consumo = 0
    lista_minima = []
    for i in range(grado_paralelizacion):
        estados_por_consumo.append(0)
    estados = []
    
    print("cores =", cores)
    print("P-states")
    for i in range(len(voltajes)):
        print("P-estado", str(i)+":", "V="+str(format((voltajes[i]), ".6f"))+",", "f="+str(format((frecuencias[i]), ".6f")))
    
    print("")
    print("##### Parte: ", parte+1)
    print("T sec\t"," =", format((tiempo_secuencial), ".2f"))
    print("P estado ","=", pestado)
    for i in range(grado_paralelizacion):
        print("particion "+str(i)+": trabajo = "+str(division_trabajo[i]))
        
    
    print("")
    print("##### Parte: ", parte+1)
    minimo_consumo, lista_minima = calculo_recursivo(estados, voltajes, frecuencias, cores, estados_por_consumo, minimo_consumo, lista_minima)
    
    return lista_minima, minimo_consumo

      
def calculo_recursivo(estados: List[int], voltajes: List[float], frecuencias: List[float], cores: int, estados_por_consumo: List[int], minimo_consumo: float, lista_minima): #Alternativa a crear tantos bucles for por cantidad de nucleos
    total = 0
    
    estados.append(0)
    for i in range(0, len(voltajes)):
        estados[len(estados) - 1] = i #modificamos únicamente el último valor
        if (len(estados) < len(division_trabajo)):
            minimo_consumo, lista_minima = calculo_recursivo(estados, voltajes, frecuencias, cores, estados_por_consumo, minimo_consumo, lista_minima)
                  
        else: #Solo se ejecuta cuando tenemos una combinación entera de estados
            tiempos = calcula_tiempo(estados, tiempo_secuencial, grado_paralelizacion, division_trabajo)
            ind_tiempos_ordenados = (sorted(range(len(tiempos)), key=lambda k: tiempos[k])) #Para poder separar potencias bien cada vez que un nucleo para, ordenado por tiempo de menor a mayor
            potencias = calcula_potencia(coreC, frecuencias, voltajes)
            for i in range(len(ind_tiempos_ordenados)):
                estados_por_consumo[i] = estados[ind_tiempos_ordenados[i]]
            
            ind = 0
            cant_nucleos_parados = 0   
            while ind < len(division_trabajo):
                potencia_combinada = 0
                for i in range(ind, len(estados_por_consumo)):
                    potencia_combinada += round(potencias[estados_por_consumo[i]], 6)
                if(ind > 0):
                    total += round((tiempos[ind_tiempos_ordenados[ind]] - tiempos[ind_tiempos_ordenados[ind - 1]]), 6) * round((wbase + potencia_combinada + wcoreinactivo * cant_nucleos_parados), 6)
                else: 
                    total += round(tiempos[ind_tiempos_ordenados[0]], 6) * round((wbase + potencia_combinada + wcoreinactivo * cant_nucleos_parados), 6)
                cant_nucleos_parados += 1
                ind += 1 
            
            total = float(format(total / 1000 / 3600, ".6f"))
            
            tiempos = arreglar_tiempos(tiempos)
            lista_salida = []
            for i in range(cores):
                if (i < len(estados)):
                    lista_salida.append("P"+str(estados[i])) 
                else:
                    lista_salida.append("--")
            lista_salida.append(" : ")
            for i in range(cores):
                if (i < len(estados)):
                    lista_salida.append(format(tiempos[i], "7.2f"))
                    lista_salida.append("")
                else:
                    lista_salida.append(format(0.00, "7.2f"))
                    lista_salida.append("")
            #cadena = cadena, " tmax =", format(max(tiempos), "7.2f"), " Energia=", str(format(total, ".6f")), "kWh"
            lista_salida.append("tmax =")
            lista_salida.append(format(max(tiempos), "7.2f"))
            lista_salida.append(" Energia=")
            lista_salida.append(str(format(total, ".6f")))
            lista_salida.append("kWh")

            if (minimo_consumo == 0 or minimo_consumo > total):
                minimo_consumo = total
                lista_minima = lista_salida
            for i in range(len(lista_salida)):
                print(lista_salida[i], end=" ")
            print("")
    estados.pop() #Para evitar que al subir en recursividad, la lista esté ya con el máximo de elementos       
    return minimo_consumo, lista_minima
        
def mostrar_resultado_final(consumo_total:int, lista_partes):
    print("")
    print("Configuracion para consumo minimo:")
    for i in range(len(lista_partes)):
        print("##### Parte:", i+1)
        for j in range(len(lista_partes[i])):
            print(lista_partes[i][j], end=" ")
        print("")
    print("")
    print("Consumo total minimo:", str(format(consumo_total, ".6f")),"kWh")

if __name__ == "__main__":
    listado = read_data(sys.stdin)
    #cores, wbase, wcoreinactivo, coreC, frecuencias, voltajes, tiempo_secuencial, pestado, grado_paralelizacion, division_trabajo = procesar_datos(listado)
    cores, wbase, wcoreinactivo, coreC, frecuencias, voltajes, cant_partes = procesar_datos(listado)
    lista_partes = []
    consumo_total = 0
    lista = []
    consumo = 0
    for i in range(int(cant_partes)):
        tiempo_secuencial, pestado, grado_paralelizacion, division_trabajo = procesar_partes(listado, i)
        lista, consumo = process(cores, wbase, wcoreinactivo, coreC, frecuencias, voltajes, tiempo_secuencial, pestado, grado_paralelizacion, division_trabajo, i)
        consumo_total += consumo
        lista_partes.append(lista)
    mostrar_resultado_final(consumo_total, lista_partes)
    