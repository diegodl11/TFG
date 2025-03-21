#include <vcg/complex/complex.h>
#include <vcg/complex/algorithms/update/topology.h>
#include <vcg/complex/algorithms/update/flag.h>
#include <vcg/complex/algorithms/hole.h> // Necesario para Hole::GetInfo
#include <vcg/complex/allocate.h> // Necesario para DeleteFace y CompactFaceVector
#include<wrap/io_trimesh/import_ply.h>
#include<wrap/io_trimesh/export_ply.h>
#include <vcg/complex/algorithms/clean.h>


// Definiciones de malla (MyFace, MyVertex, MyMesh) - asume que ya están definidas
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

void eliminarBordesAgujeros(MyMesh& m, int tamanoMaximoAgujero) {

    m.face.EnableFFAdjacency();
    //  Actualizar la topología
    tri::UpdateTopology<MyMesh>::FaceFace(m);
    // ... (code to load, enable, and compute FF-adjacency) ...
    if (!tri::Clean<MyMesh>::IsFFAdjacencyConsistent(m)) {
        std::cerr << "Error: Face-face adjacency is inconsistent." << std::endl;
        // Handle the error appropriately, perhaps by inspecting the mesh for non-manifold issues
    }
    
    //  Identificar las aristas de borde
    tri::UpdateFlags<MyMesh>::FaceBorderFromFF(m);

    //  Obtener información de los agujeros
    std::vector<tri::Hole<MyMesh>::Info> agujeros;
    tri::Hole<MyMesh>::GetInfo(m, false, agujeros);
    cout<<"agua: "<<agujeros.size()<<endl;
    // Iterar sobre los agujeros y marcar los bordes para eliminar
    std::vector<MyMesh::FacePointer> carasAEliminar;
    for (const auto& agujero : agujeros) {
        
        if (agujero.size <= tamanoMaximoAgujero) {
            // Recorrer el borde del agujero y marcar las caras
            
            vcg::face::Pos<MyFace> pos = agujero.p;
            do {
                MyMesh::FacePointer cara = pos.f;
                if (cara && !cara->IsD()) {
                    carasAEliminar.push_back(cara);
                    //cara->SetD(); // Marcar para eliminar
                }
                pos.NextB();
            } while (pos != agujero.p);
        }
    }
    
     // Eliminar las caras marcadas
    std::set<MyMesh::FacePointer> carasAEliminarSet(carasAEliminar.begin(), carasAEliminar.end());

    for (MyMesh::FacePointer cara : carasAEliminarSet) {
        if (cara && !cara->IsD()) {  // 🔍 Evita llamar DeleteFace en una cara ya eliminada
            tri::Allocator<MyMesh>::DeleteFace(m, *cara);
        }
    }

    // Compactar el vector de caras
    std::cout << "Número de caras antes de compactar: " << m.face.size() << std::endl;
    tri::Allocator<MyMesh>::CompactFaceVector(m);
    std::cout << "Número de caras después de compactar: " << m.face.size() << std::endl;

    //  Eliminar vértices no referenciados antes de compactar
    tri::Clean<MyMesh>::RemoveUnreferencedVertex(m);
    std::cout << "Vértices no referenciados eliminados" << std::endl;

    //  Compactar vértices
    tri::Allocator<MyMesh>::CompactVertexVector(m);
    std::cout << "Número de vértices después de compactar: " << m.vert.size() << std::endl;

    // actualizar `vn`
    //m.vn = m.vert.size();
    std::cout << "Número de vértices actualizado: " << m.vn << std::endl;

    // Verificación antes de exportar
    if (m.vn != m.vert.size()) {
        std::cerr << "⚠️ ERROR: m.vn no coincide con m.vert.size() antes de exportar" << std::endl;
    }  
  
}

int main( int argc, char **argv )
{
    MyMesh startMesh;
    if(argc < 3 )
    {
        printf("Usage: ./cerrar_agujeros <input_ply_file> <output_ply_file> [holeSize] \n");
        return -1;
    }
    int ret= tri::io::ImporterPLY<MyMesh>::Open(startMesh,argv[1]);
    if(ret!=0)
    {
        printf("Unable to open %s for '%s'\n",argv[1],tri::io::ImporterPLY<MyMesh>::ErrorMsg(ret));
        return -1;
    }
    int holeSize =(argc > 3) ? atoi(argv[3]) : 100;
    eliminarBordesAgujeros(startMesh, holeSize);
    
    std::cout << "Verificación final antes de exportar:\n";
    std::cout << "Número de caras en la malla: " << startMesh.fn << ", número real en el vector: " << startMesh.face.size() << std::endl;
    std::cout << "Número de vértices en la malla: " << startMesh.vn << ", número real en el vector: " << startMesh.vert.size() << std::endl;
    assert(startMesh.fn == startMesh.face.size());
    assert(startMesh.vn == startMesh.vert.size());

    tri::io::ExporterPLY<MyMesh>::Save(startMesh,argv[2],tri::io::Mask::IOM_VERTCOLOR|tri::io::Mask::IOM_WEDGTEXCOORD );
    return 0;
}





