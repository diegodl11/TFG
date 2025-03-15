#include<vcg/complex/complex.h>
#include<vcg/complex/algorithms/create/platonic.h>

#include <vcg/complex/algorithms/update/bounding.h>
#include <vcg/space/index/spatial_hashing.h>
#include<wrap/io_trimesh/import_ply.h>
#include<wrap/io_trimesh/export_ply.h>
#include <vcg/complex/algorithms/pointcloud_normal.h>
#include<vcg/space/outline2_packer.h>
#include <iostream>
#include <chrono>

using namespace vcg;
using namespace std;

class MyEdge;
class MyFace;
class MyVertex;
struct MyUsedTypes : public UsedTypes<	Use<MyVertex>   ::AsVertexType,
                                        Use<MyEdge>     ::AsEdgeType,
                                        Use<MyFace>     ::AsFaceType>{};

class MyVertex  : public Vertex<MyUsedTypes, vertex::InfoOcf, vertex::Coord3f, vertex::Normal3f, vertex::TexCoord2f, vertex::VFAdj , vertex::Qualityf, vertex::Color4b, vertex::BitFlags  >{};
class MyFace    : public Face< MyUsedTypes, face::InfoOcf, face::VertexRef, face::CurvatureDirf, face::BitFlags, face::FFAdjOcf ,face::VFAdj , face::WedgeTexCoord2f> {};
class MyEdge    : public Edge< MyUsedTypes>{};
class MyMesh    : public tri::TriMesh< vertex::vector_ocf<MyVertex>, face::vector_ocf<MyFace> , vector<MyEdge>  > {};

int main( int argc, char **argv )
{
    MyMesh startMesh;
    if(argc < 3) {
        std::cout << "Usage: ./normal_filter <input_ply_file> <output_ply_file> [fittingAdjNum] [smoothingIterNum] [useViewPoint] [viewPointX] [viewPointY] [viewPointZ]\n" << std::endl;
        return -1;
    }

    //printf("Reading %s \n",argv[1]);
    int ret= tri::io::ImporterPLY<MyMesh>::Open(startMesh,argv[1]);
    if(ret!=0)
    {
        printf("Unable to open %s for '%s'\n",argv[1],tri::io::ImporterPLY<MyMesh>::ErrorMsg(ret));
        return -1;
    }

    // Configuración de parámetros con valores por defecto
    tri::PointCloudNormal<MyMesh>::Param p;
    p.fittingAdjNum = (argc > 3) ? atoi(argv[3]) : 10; // Número de vecinos para el ajuste de normales
    p.smoothingIterNum = (argc > 4) ? atoi(argv[4]) : 0; // Número de iteraciones de suavizado
    p.useViewPoint = (argc > 5) ? atoi(argv[5]) != 0 : false; // Activar uso del punto de vista

    // Punto de vista
    if (argc > 8) {
        float x = atof(argv[6]);
        float y = atof(argv[7]);
        float z = atof(argv[8]);
        p.viewPoint = vcg::Point3f(x, y, z);
    } else {
        p.viewPoint = vcg::Point3f(0, 0, 0); // Valor por defecto
    }

    // Captura del tiempo inicial
    //auto inicio = std::chrono::high_resolution_clock::now();
    tri::PointCloudNormal<MyMesh>::Compute(startMesh, p);
    
    // Captura del tiempo final
    //auto fin = std::chrono::high_resolution_clock::now();
    //auto duracion = std::chrono::duration_cast<std::chrono::microseconds>(fin - inicio);

    // Impresión del resultado
    //std::cout << "Tiempo de ejecución: " << duracion.count() << " microsegundos" << std::endl;
     
    // Guardar la malla con las normales calculadas
    if (tri::io::ExporterPLY<MyMesh>::Save(startMesh, argv[2], tri::io::Mask::IOM_VERTCOLOR|tri::io::Mask::IOM_VERTNORMAL) != 0) {
        cerr << "Output file saving failed" << endl;
        return -1;
    }

    return 0;
}


